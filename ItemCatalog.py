from flask import Flask, render_template, request
from flask import redirect, jsonify, url_for, flash
from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from db_setup import Base, Category, Item, User
from flask import session as login_session
import random
import string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests
app = Flask(__name__)

CLIENT_ID = json.loads(open('client_secrets.json', 'r')
                       .read())['web']['client_id']
APPLICATION_NAME = "Web client 2"
# Connect to Database Create database session.
# Eliminate issues to multiple threaded connections.
engine = create_engine('sqlite:///categorywithusers.db',
                       connect_args={'check_same_thread': False},
                       poolclass=StaticPool, echo=True)

Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


# Create anti-forgery state token
@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    # return "The current session state is %s" % login_session['state']
    return render_template('login.html', STATE=state)


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    print login_session['state']
    print request.args
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        print response
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        print result['issued_to']
        print CLIENT_ID
        response.headers['Content-Type'] = 'application/json'
        return response
    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response
        (json.dumps(
            'Current user is already connected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    # login_session['credentials'] = credentials.to_json()
    login_session['gplus_id'] = gplus_id
    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)
    data = answer.json()
    print login_session
    # Check if user has "username", if no username insert email instead.
    try:
        login_session['username'] = data['name']
    except KeyError:
        login_session['username'] = data['email']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']
    login_session['id'] = data['id']
    # See if a user exists, if it doesn't make a new one
    user = session.query(User).filter_by(
            email=login_session['email']).one_or_none()
    if user is None:
        newUser = User(name=login_session['username'], email=login_session[
            'email'], picture=login_session['picture'])
        session.add(newUser)
        session.commit()
        user = session.query(User).filter_by(
            email=login_session['email']).one()
        print user.id, user.email
        print "New User Created"

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 1'
    output += '50px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("logged in as %s" % login_session['username'])
    print "done!"
    print login_session
    return output


def getUserInfo(user_id):
    print "get User Info"
    user = session.query(User).filter_by(id='user_id').one_or_none()
    return user


def getUserID(email):
    print "get User ID"
    user = session.query(User).filter_by(email=email).one()
    return user.id


@app.route('/gdisconnect')  # Disconnect user and revoke token.
def gdisconnect():
    access_token = login_session.get('access_token')
    print access_token
    if access_token is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    print result
    print result['content-length']
    # Check User's status and if Token has expired.
    if result['content-length'] == '81':
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']

        response = make_response(json.dumps(
            'Successfully disconnected.Token had expired'), 200)
        response.headers['Content-Type'] = 'application/json'
        return redirect('/category')
    if result['status'] == '200':
        # Reset a user's session.
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']

        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return redirect('/category')
    else:
        # If the given token was invalid.
        response = make_response(
            json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return redirect('/category')


# JSON APIs to view Category's Itemized Information
@app.route('/category/<int:category_id>/items/JSON')
def categoryItemJSON(category_id):
    category = session.query(Category).filter_by(id=category_id).one()
    items = session.query(Item).filter_by(
        category_id=category_id).all()
    return jsonify(Items=[i.serialize for i in items])


@app.route('/category/<int:category_id>/items/<int:item_id>/JSON')
def ItemJSON(category_id, item_id):
    item = session.query(Item).filter_by(id=item_id).one()
    return jsonify(Item=item.serialize)


@app.route('/category/JSON')
def categoriesJSON():
    categories = session.query(Category).all()
    return jsonify(categories=[r.serialize for r in categories])


# Show Categories
@app.route('/')
@app.route('/category/')
def showCategories():
    category = session.query(Category).order_by(asc(Category.name))
    return render_template('categories.html', category=category)


# Create new Category
@app.route('/category/new/', methods=['GET', 'POST'])
def newCategory():
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        user = session.query(
            User).filter_by(email=login_session['email']).one()
        newCategory = Category(
            name=request.form['name'], user_id=user.id)
        session.add(newCategory)
        print newCategory.user_id
        print login_session['id']
        flash('New Category %s Successfully Created' % newCategory.name)
        session.commit()
        return redirect(url_for('showCategories'))
    else:
        return render_template('newcategory.html')

# Edit Category


@app.route('/category/<int:category_id>/edit/', methods=['GET', 'POST'])
def editCategory(category_id):
    if 'username' not in login_session:
        return redirect('/login')
    # Authorization Check
    editedCategory = session.query(
        Category).filter_by(id=category_id).one()
    userToCheck = session.query(
        User).filter_by(email=login_session['email']).one()
    if editedCategory.user_id != userToCheck.id:
        # Alert if failed the Check
        return "<script>function myFunction() {alert('You\
         are not authorized to edit this Category.\
         ');}</script><body onload='myFunction()'>"
    if request.method == 'POST':
        if request.form['name']:
            editedCategory.name = request.form['name']
            flash('Category Successfully Edited %s' % editedCategory.name)
            return redirect(url_for('showCategories'))
    else:
        return render_template('editcategory.html', category=editedCategory)


# Delete Category
@app.route('/category/<int:category_id>/delete/', methods=['GET', 'POST'])
def deleteCategory(category_id):
    if 'username' not in login_session:
        return redirect('/login')
    # Authorization Check
    categoryToDelete = session.query(
        Category).filter_by(id=category_id).one()
    userToCheck = session.query(
        User).filter_by(email=login_session['email']).one()
    if categoryToDelete.user_id != userToCheck.id:
        # Alert if failed the Check
        return "<script>function myFunction() {alert('You\
         are not authorized to delete this Category.\
         ');}</script><body onload='myFunction()'>"
    if request.method == 'POST':
        session.delete(categoryToDelete)
        flash('%s Successfully Deleted' % categoryToDelete.name)
        session.commit()
        return redirect(url_for('showCategories', category_id=category_id))
    else:
        return render_template(
            'deletecategory.html', category=categoryToDelete)


# Show a Category's Items
@app.route('/category/<int:category_id>/')
@app.route('/category/<int:category_id>/items/')
def showItem(category_id):
    category = session.query(Category).filter_by(id=category_id).one()
    item = session.query(Item).filter_by(category_id=category_id).all()
    return render_template('item.html', item=item, category=category)


# Create an item
@app.route('/category/<int:category_id>/items/new/', methods=['GET', 'POST'])
def newItem(category_id):
    if 'username' not in login_session:
        return redirect('/login')
    category = session.query(Category).filter_by(id=category_id).one()
    if request.method == 'POST':
        newItem = Item(name=request.form['name'], description=request.form[
            'description'], price=request.form[
                'price'], category_id=category_id, user_id=category.user_id)
        session.add(newItem)
        session.commit()
        flash('%s Item Created' % (newItem.name))
        return redirect(url_for('showItem', category_id=category_id))
    else:
        return render_template('newitem.html', category_id=category_id)

# Edit an item


@app.route('/category/<int:category_id>/items/<int:item_id>/edit',
           methods=['GET', 'POST'])
def editItem(category_id, item_id):
    if 'username' not in login_session:
        return redirect('/login')
    editedItem = session.query(Item).filter_by(id=item_id).one()
    # Authorization Check
    category = session.query(
        Category).filter_by(id=category_id).one()
    userToCheck = session.query(
        User).filter_by(email=login_session['email']).one()
    if category.user_id != userToCheck.id:
        # Alert if failed the Check
        return "<script>function myFunction() {alert('You\
         are not authorized to edit this item.\
         ');}</script><body onload='myFunction()'>"
    if request.method == 'POST':
        if request.form['name']:
            editedItem.name = request.form['name']
        if request.form['description']:
            editedItem.description = request.form['description']
        if request.form['price']:
            editedItem.price = request.form['price']
        session.add(editedItem)
        session.commit()
        flash('Item Edited')
        return redirect(url_for('showItem', category_id=category_id))
    else:
        return render_template(
            'edititem.html', category_id=category_id,
            item_id=item_id, item=editedItem)


# Delete an item
@app.route('/category/<int:category_id>/items/<int:item_id>/delete',
           methods=['GET', 'POST'])
def deleteItem(category_id, item_id):
    if 'username' not in login_session:
        return redirect('/login')
    itemToDelete = session.query(Item).filter_by(id=item_id).one()
    # Authorization Check
    category = session.query(
        Category).filter_by(id=category_id).one()
    userToCheck = session.query(
        User).filter_by(email=login_session['email']).one()
    if category.user_id != userToCheck.id:
        # Alert if failed the Check
        return "<script>function myFunction() {alert('You\
         are not authorized to delete this item.\
         ');}</script><body onload='myFunction()'>"
    if request.method == 'POST':
        session.delete(itemToDelete)
        session.commit()
        flash('Item Deleted')
        return redirect(url_for('showItem', category_id=category_id))
    else:
        return render_template('deleteItem.html', item=itemToDelete)


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
