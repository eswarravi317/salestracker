from flask import Flask, render_template, request, redirect, jsonify, session, flash
import joblib
import os
import numpy as np
from datetime import timedelta
from flask_mysqldb import MySQL
import MySQLdb.cursors
import re
import random
from apyori import apriori

app = Flask(__name__)

app.secret_key = 'salesPredictionsecretKey'
app.permanent_session_lifetime = timedelta(minutes=60)
  
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'salestracker'
  
mysql = MySQL(app)


# home or login
@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def index():
    session.pop('loggedin', None)
    session.pop('userid', None)
    session.pop('name', None)
    session.pop('email', None)
    if request.method == 'POST' and 'email' in request.form and 'password' in request.form:
        email = request.form['email']
        password = request.form['password']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM providers WHERE email = % s', (email, ))
        user = cursor.fetchone()
        if user:
            if user['password'] == password:
                session['loggedin'] = True
                session['userid'] = user['provider_id']
                session['name'] = user['name']
                session['email'] = user['email']
                return redirect('/dashboard')
            else:
                flash('Password might be wrong!')
        else:
            flash('User doesn\'t exists!')
    return render_template('index.html')

# register
@app.route('/register', methods =['GET', 'POST'])
def register():
    session.pop('loggedin', None)
    session.pop('userid', None)
    session.pop('name', None)
    session.pop('email', None)
    if request.method == 'POST' and 'name' in request.form and 'email' in request.form and 'password' in request.form and 'location' in request.form and 'outlet_year' in request.form and 'outlet_size' in request.form and 'outlet_location' in request.form and 'outlet_type' in request.form:
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        location = request.form['location']
        outlet_year = request.form['outlet_year']
        outlet_size = request.form['outlet_size']
        outlet_location = request.form['outlet_location']
        outlet_type = request.form['outlet_type']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM providers WHERE email = % s', (email, ))
        account = cursor.fetchone()
        if account:
            flash('Account already exists !')
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            flash('Invalid email address !')
        elif not name or not password or not email:
            flash('Please fill out the form !')
        else:
            cursor.execute('CREATE TABLE `salestracker`.`% s` (`tid` INT NOT NULL AUTO_INCREMENT , PRIMARY KEY (`tid`))', (email.split('@')[0],))
            cursor.execute('INSERT INTO providers VALUES ("null", % s, % s, % s)', (name, email, password))
            cursor.execute('INSERT INTO outlet VALUES (% s, % s, % s, % s, % s, % s)', (email, location, outlet_year, outlet_size, outlet_location, outlet_type))
            mysql.connection.commit()
            return redirect('/login')
    elif request.method == 'POST':
        flash('Please fill out the form !')
    return render_template('register.html')

# dashboard
@app.route('/dashboard')
def dashboard():
    if 'loggedin' in session:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        cursor.execute('SELECT * FROM products WHERE provider_id = % s', (session['email'], ))
        product = cursor.fetchall()

        cursor.execute('SELECT * FROM outlet WHERE outlet_id = % s', (session['email'], ))
        outlet = cursor.fetchone()

        outlet_establishment_year = outlet['outlet_year']
        outlet_size = outlet['outlet_size_id']
        outlet_location_type = outlet['outlet_location_type_id']
        outlet_type = outlet['outlet_type_id']

        values = []

        for item in product:
            datas = {}

            cursor.execute('SELECT * FROM orders WHERE provider_id = % s and name = % s', (session['email'], item['name']))
            available_data = cursor.fetchall()

            if len(available_data):
                cursor.execute('SELECT sum(quantity) as weight, min(total_mrp) as total_mrp FROM orders WHERE provider_id = % s and name = % s', (session['email'], item['name']))
                weight_mrp = cursor.fetchone()
                item_weight = weight_mrp['weight']
                item_fat_content= float(item['fat_id'])
                item_visibility = 0
                if item['visibility'] == "High":
                    item_visibility = float(random.randint(80, 100)/1000)
                elif item['visibility'] == "Medium":
                    item_visibility = float(random.randint(50, 79)/1000)
                elif item['visibility'] == "Low":
                    item_visibility = float(random.randint(0, 49)/1000)
                item_type= float(item['type_id'])
                item_mrp = weight_mrp['total_mrp']
                
                X= np.array([[item_weight, item_fat_content, item_visibility, item_type, item_mrp, outlet_establishment_year, outlet_size, outlet_location_type, outlet_type]])
                scaler_path = r'D:\Learning\SalesTracker\models\sc.sav'
                sc=joblib.load(scaler_path)
                X_std= sc.transform(X)
                model_path = r'D:\Learning\SalesTracker\models\lr.sav'
                model= joblib.load(model_path)
                Y_pred=model.predict(X_std)
                predict = round(abs(float(Y_pred)))
                
                datas = {'name': item['name'], 'actual': item_mrp, 'predict': predict}
                values.append(datas)
        if product and outlet and len(values):
            return render_template('dashboard.html', account = outlet, data = values)
        else:
            return render_template('dashboard.html', account = "None", data = "None")

    return redirect('/')

# statistics
@app.route('/statistics')
def statistics():
    if 'loggedin' in session:
        records = []
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM `% s`", (session['email'].split('@')[0], ))
        products = cursor.fetchall()
        for i in range(0, len(products)):
            del products[i]['tid']

        for i in range(0, len(products)):
            record_lines = list(products[i].values())
            records.append(record_lines)

        # build apriori model
        association_rules = apriori(records, min_support = 0.7, min_confidence = 0.9, min_lift = 1.2, min_length = 2)
        association_rules = list(association_rules)
        # print(association_rules)

        predicted_reletions = []

        for item in association_rules:
            
            # first index of the inner list
            # Contains base item and add item
            pair = item[0] 
            items = [x for x in pair]
            # print("Rule: " + items[0] + " -> " + items[1])
            elem = items[0] + " -> " + items[1]
            if elem not in predicted_reletions:
                predicted_reletions.append(elem)

        # print(predicted_reletions)

        if len(predicted_reletions):
            return render_template('statistics.html', data = predicted_reletions)
        return render_template('statistics.html', data = "None")
    return redirect('/')

ordereditems = []

# billing
@app.route('/billing')
def billing():
    if 'loggedin' in session:
        global ordereditems
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT name FROM products WHERE provider_id = % s', (session['email'], ))
        available_items = cursor.fetchall()
        if len(ordereditems):
            return render_template('billing.html', available_items = available_items, data = ordereditems)
        return render_template('billing.html', available_items = available_items, data = "None")
    return redirect('/')

# addorder
@app.route('/addorder', methods = ['GET', 'POST'])
def addorder():
    global ordereditems
    if 'loggedin' in session:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        if request.method == 'POST' and 'itemname' in request.form and 'itemcount' in request.form:
            cursor.execute('SELECT type_id, unit, mrp FROM products WHERE name = % s and provider_id = % s', (request.form['itemname'], session['email'], ))
            fetchedData = cursor.fetchone()
            mrp = float(int(fetchedData['mrp']) * int(request.form['itemcount']))
            datas = {'type_id': fetchedData['type_id'] , 'name': request.form['itemname'], 'unit': fetchedData['unit'], 'quantity': request.form['itemcount'], 'total_mrp': mrp}
            ordereditems.append(datas)
            # print(ordereditems)
        return redirect('/billing')
    return redirect('/')

# saveorder
@app.route('/saveorder', methods = ['GET', 'POST'])
def saveorder():
    global ordereditems
    if 'loggedin' in session:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        if len(ordereditems):
            rows = 0
            cursor.execute('SELECT MAX(tid) as maxid FROM `% s`', (session['email'].split('@')[0], ))
            maxrow = cursor.fetchone()
            if maxrow['maxid'] == None:
                rows = 1
            else:
                rows = int(maxrow['maxid'])+1
            # print(rows)
            cursor.execute('INSERT INTO `% s` VALUES()', (session['email'].split('@')[0], ))
            mysql.connection.commit()
            for data in ordereditems:
                cursor.execute("UPDATE `% s` SET `% s` = % s WHERE tid = % s", (session['email'].split('@')[0], data['name'], data['name'], int(rows) ))
                cursor.execute('INSERT INTO orders VALUES ("null", % s, curdate(), % s, % s, % s, % s, % s)', (session['email'], data['type_id'], data['name'], data['unit'], data['quantity'], data['total_mrp']))
                mysql.connection.commit()
            ordereditems.clear()
            return redirect('/billing')
    return redirect('/')

@app.route('/reset')
def reset():
    global ordereditems
    global orderid
    if 'loggedin' in session:
        ordereditems.clear()
        orderid = None
        return redirect('/billing')
    return redirect('/')

# addorders
# @app.route('/addorders', methods = ['GET', 'POST'])
# def addorders():
#     if 'loggedin' in session:
#         if request.method == 'POST' and 'type' in request.form and 'name' in request.form and 'quantity' in request.form:
#             print(request.form)
#     return redirect('/')

# predict
@app.route('/predict')
def predict():
    if 'loggedin' in session:
        return render_template('predict.html')
    return redirect('/')

@app.route('/prediction', methods=['POST','GET'])
def result():

    if 'loggedin' in session:
        
        item_weight= float(request.form['item_weight'])
        item_fat_content=float(request.form['item_fat_content'])
        item_visibility = request.form['item_visibility']
        if item_visibility == "High":
            item_visibility = float(random.randint(90, 100)/1000)
        elif item_visibility == "Medium":
            item_visibility = float(random.randint(80, 89)/1000)
        elif item_visibility == "Low":
            item_visibility = float(random.randint(70, 79)/1000)
        item_type= float(request.form['item_type'])
        item_mrp = float(request.form['item_mrp'])
        outlet_establishment_year= float(request.form['outlet_establishment_year'])
        outlet_size= float(request.form['outlet_size'])
        outlet_location_type= float(request.form['outlet_location_type'])
        outlet_type= float(request.form['outlet_type'])
        
        X= np.array([[ item_weight,item_fat_content,item_visibility,item_type,item_mrp,outlet_establishment_year,outlet_size,outlet_location_type,outlet_type ]])
        scaler_path= r'D:\Learning\Final_Project\models\sc.sav'
        sc=joblib.load(scaler_path)
        X_std= sc.transform(X)
        model_path=r'D:\Learning\Final_Project\models\lr.sav'
        model= joblib.load(model_path)
        Y_pred=model.predict(X_std)
        
        return jsonify({'Prediction': float(Y_pred)})

    return redirect('/')

# account
@app.route('/account')
def account():
    if 'loggedin' in session:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM providers WHERE email = % s', (session['email'], ))
        user = cursor.fetchone()
        cursor.execute('SELECT * FROM outlet WHERE outlet_id = % s', (session['email'], ))
        outlet = cursor.fetchone()
        cursor.execute('SELECT name FROM outlet_size WHERE id = % s', (outlet['outlet_size_id'], ))
        outlet_size = cursor.fetchone()
        cursor.execute('SELECT name FROM outlet_location_type WHERE id = % s', (outlet['outlet_location_type_id'], ))
        outlet_location = cursor.fetchone()
        cursor.execute('SELECT name FROM outlet_type WHERE id = % s', (outlet['outlet_type_id'], ))
        outlet_type = cursor.fetchone()
        cursor.execute('SELECT * FROM products WHERE provider_id = % s', (session['email'], ))
        data = cursor.fetchall()
        # for items in data:
        #     cursor.execute('SELECT name FROM product_type WHERE id = % s', (items['type_id']))
        #     items['type_id'] = cursor.fetchone()['name']
        if user and outlet and data:
            return render_template('account.html', user = user, outlet = outlet, outlet_size = outlet_size, outlet_location = outlet_location, outlet_type = outlet_type, data = data)
        else:
            return render_template('account.html', user = user, outlet = outlet, outlet_size = outlet_size, outlet_location = outlet_location, outlet_type = outlet_type, data = "None")
    return redirect('/')

# add item
@app.route('/additem', methods =['GET', 'POST'])
def additem():
    if request.method == 'POST' and 'loggedin' in session:
        type = request.form['item_type']
        name = request.form['item_name']
        fat = request.form['item_fat_content']
        visibility = request.form['item_visibility']
        unit = request.form['item_unit']
        quantity = request.form['item_quantity']
        mrp = request.form['item_mrp']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('ALTER TABLE `% s` ADD `% s` VARCHAR(100) NOT NULL DEFAULT "NaN"', (session['email'].split('@')[0], name))
        cursor.execute('INSERT INTO products VALUES ("null", % s, % s, % s, % s, % s, % s, % s, % s)', (session['email'], type, name, fat, visibility, unit, quantity, mrp))
        mysql.connection.commit()
        return redirect('/account')
    return render_template('dashboard.html')

# help
@app.route('/help')
def help():
    if 'loggedin' in session:
        return render_template('help.html')
    return redirect('/')

# bestlocations
@app.route('/bestlocations', methods=['POST','GET'])
def bestlocations():
    if 'loggedin' in session:
        item_name = request.form['item_name']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM products WHERE name = % s and provider_id != % s', (item_name, session['email'], ))
        data = cursor.fetchall()

        values = []

        for item in data:
            datas = {}
            email = item['provider_id']
            cursor.execute('SELECT * FROM outlet WHERE outlet_id = % s', (email, ))
            outlet = cursor.fetchone()

            outlet_establishment_year = outlet['outlet_year']
            outlet_size = outlet['outlet_size_id']
            outlet_location_type = outlet['outlet_location_type_id']
            outlet_type = outlet['outlet_type_id']

            cursor.execute('SELECT * FROM orders WHERE provider_id = % s and name = % s', (email, item_name))
            available_data = cursor.fetchall()
            # print(available_data)

            if len(available_data):
                cursor.execute('SELECT sum(quantity) as weight, sum(total_mrp) as total_mrp FROM orders WHERE provider_id = % s and name = % s', (email, item_name))
                weight_mrp = cursor.fetchone()
                item_weight = weight_mrp['weight']
                item_fat_content= float(item['fat_id'])
                item_visibility = 0
                if item['visibility'] == "High":
                    item_visibility = float(random.randint(90, 100)/1000)
                elif item['visibility'] == "Medium":
                    item_visibility = float(random.randint(80, 89)/1000)
                elif item['visibility'] == "Low":
                    item_visibility = float(random.randint(70, 79)/1000)
                item_type= float(item['type_id'])
                item_mrp = weight_mrp['total_mrp']
                
                X= np.array([[item_weight, item_fat_content, item_visibility, item_type, item_mrp, outlet_establishment_year, outlet_size, outlet_location_type, outlet_type]])
                scaler_path = r'D:\Learning\SalesTracker\models\sc.sav'
                sc=joblib.load(scaler_path)
                X_std= sc.transform(X)
                model_path = r'D:\Learning\SalesTracker\models\lr.sav'
                model= joblib.load(model_path)
                Y_pred=model.predict(X_std)
                predict = round(abs(float(Y_pred)))

                datas = {'location': outlet['outlet_location'], 'predict': predict}
                values.append(datas)

        if values:
            return render_template('help.html', data = values, input = item_name)
        else:
            return render_template('help.html', data = "None", input = "None")
    return redirect('/')

@app.route('/bestitems', methods=['POST','GET'])
def bestitems():
    if 'loggedin' in session:
        location = request.form['location']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        cursor.execute('SELECT * FROM outlet WHERE outlet_location = % s and outlet_id != % s', (location, session['email'], ))
        data = cursor.fetchall()

        values = []

        for outlet in data:
            datas = {}
            email = outlet['outlet_id']

            outlet_establishment_year = outlet['outlet_year']
            outlet_size = outlet['outlet_size_id']
            outlet_location_type = outlet['outlet_location_type_id']
            outlet_type = outlet['outlet_type_id']

            cursor.execute('SELECT * FROM products WHERE provider_id = % s', (email, ))
            productdata = cursor.fetchall()
            
            for item in productdata:
                cursor.execute('SELECT * FROM orders WHERE provider_id = % s and name = % s', (email, item['name']))
                available_data = cursor.fetchall()

                if len(available_data):
                    cursor.execute('SELECT sum(quantity) as weight, sum(total_mrp) as total_mrp FROM orders WHERE provider_id = % s and name = % s', (email, item['name']))
                    weight_mrp = cursor.fetchone()
                    item_weight = weight_mrp['weight']
                    item_fat_content= float(item['fat_id'])
                    item_visibility = 0
                    if item['visibility'] == "High":
                        item_visibility = float(random.randint(90, 100)/1000)
                    elif item['visibility'] == "Medium":
                        item_visibility = float(random.randint(80, 89)/1000)
                    elif item['visibility'] == "Low":
                        item_visibility = float(random.randint(70, 79)/1000)
                    item_type= float(item['type_id'])
                    item_mrp = weight_mrp['total_mrp']

                    X= np.array([[item_weight, item_fat_content, item_visibility, item_type, item_mrp, outlet_establishment_year, outlet_size, outlet_location_type, outlet_type]])
                    scaler_path = r'D:\Learning\SalesTracker\models\sc.sav'
                    sc=joblib.load(scaler_path)
                    X_std= sc.transform(X)
                    model_path = r'D:\Learning\SalesTracker\models\lr.sav'
                    model= joblib.load(model_path)
                    Y_pred=model.predict(X_std)
                    predict = round(abs(float(Y_pred)))
                    
                    datas = {'item': item['name'], 'predict': predict}
                    values.append(datas)
        if values:
            return render_template('help.html', datas = values, inputs = location)
        else:
            return render_template('help.html', datas = "None", inputs = "None")
 
    return redirect('/')

# logout
@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('userid', None)
    session.pop('name', None)
    session.pop('email', None)
    return redirect('/')


# for debugging
if __name__ == "__main__":
    app.run(debug=True)