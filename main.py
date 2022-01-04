# -*- coding: utf-8 -*-

# ---------------------------------------- Imports FLASK ---------------------------------------------------------------
from flask import Flask, flash, request, redirect, url_for, render_template, session, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sockets import Sockets
import json
import xlsxwriter
active_clients = list()


# ---------------------------------------- Imports GOOGLE ---------------------------------------------------------------
from google.oauth2 import service_account 
from google.cloud import datastore
key_location = "analog-context-251208-2b5a423e71e8.json"
credentials = service_account.Credentials.from_service_account_file(key_location)
datastore_client = datastore.Client(project="analog-context-251208", credentials=credentials)



# ---------------------------------------- Imports STRIPE ---------------------------------------------------------------
import stripe
import os
import datetime
from datetime import timedelta

stripe_keys = {
  'secret_key': os.environ['SECRET_KEY'],
  'publishable_key': os.environ['PUBLISHABLE_KEY']
}

stripe.api_key = stripe_keys['secret_key']





# ------------------------------------ Imports MAILJET --------------------------------------------------------------------------
import mailjet_rest

MAILJET_API_KEY = os.environ['MAILJET_API_KEY']
MAILJET_API_SECRET = os.environ['MAILJET_API_SECRET']
MAILJET_SENDER = os.environ['MAILJET_SENDER']








# ---------------------------------------- Flask and sockets setup ---------------------------------------------------------------
app = Flask(__name__)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'
sockets = Sockets(app)

        







# ----------------- gcloud storage-related functions ------------------------
def create_new_unap_entry(username, password):
    key = datastore_client.key('MK_User', username)
    entity = datastore.Entity(key=key)
    entity.update({'username': username, 'password': generate_password_hash(password), 'balance': 0.25, 'archive': [], 'outgoing': []}) 
    datastore_client.put(entity)

         







# -------------------- mailjet-related functions --------------------------------------------
def send_email(to, contents, username):
    client = mailjet_rest.Client(
        auth=(MAILJET_API_KEY, MAILJET_API_SECRET), version='v3.1')
    
    message = "<p>" + str(contents)
    data = {
        'Messages': [{
            "From": {
                    "Email": MAILJET_SENDER,
                    "Name": 'Email from bb.com'
            },
            "To": [{
                "Email": to
            }],
            "Subject": username,
            "TextPart": message,
            "HTMLPart": message
        }]
    }      
    client.send.create(data=data)   










#-------------------------------------------------- flask-Sockets event handler / dispatcher  -----------------------------------------#
@sockets.route('/chat')
def chat_socket(ws):
    while not ws.closed:
        m = ws.receive()
        if m is None:  # message is "None" if the client has closed.
            continue
        
        message = json.loads(m)
        typ = message.get('type')
        
        # somebody joined, get their name and address
        if typ == "joined":
            un = message.get('username')
            if un in active_clients:
                print(un,"refreshed their browser")
                active_clients[active_clients.index(un)+1] = ws.handler.active_client.address
            else:
                print(un,"joined")
                active_clients.append(un)
                active_clients.append(ws.handler.active_client.address)
            
        # somebody left, delete their name and address
        if typ == "left":
            un = message.get('username')
            print(un,"left")
            del active_clients[active_clients.index(un) + 1]
            del active_clients[active_clients.index(un)]

        
        # check the day and time, and adjust the translation delivery message accordingly
        if typ == "check":
            
            clients = ws.handler.server.clients.values()
            
            day = datetime.datetime.today().weekday()
            hour = int(str((datetime.datetime.utcnow() + timedelta(hours=9))).split(" ")[1].split(':')[0])
            
            if day > 4:
                p = dict({'type': 'result', 'delivery': 'monday_by_11'})
            else:
                if 22 > hour > 16:
                    p = dict({'type': 'result', 'delivery': 'tonight_by_23'})
                if 22 < hour <= 24:
                    p = dict({'type': 'result', 'delivery': 'tomorrow_by_11'})
                if hour < 9:
                    p = dict({'type': 'result', 'delivery': 'today_by_11'})
                if (8 < hour < 16):
                    p = dict({'type': 'result', 'delivery': 'now'})
                            
            packet = json.dumps(p)
            clients = ws.handler.server.clients.values()
            for client in clients:
                client.ws.send(packet)



        
        # mk is checking for backlogged messages
        if typ == "backlog_check":
            
            key = datastore_client.key('MK_User', "mk")
            entity_in_question = datastore_client.get(key)
            archive = entity_in_question['archive']
            archive_list = list(archive)
            
            if len(archive_list) > 1:
                
                for bc in range(3, len(archive_list), 4):
                    
                    type_of_inquiry = archive_list[bc-3]
                    delivery = archive_list[bc-2]
                    question = archive_list[bc-1]
                    asker = archive_list[bc]
            
                    p = dict({'type': 'question_relay', 'subtype': type_of_inquiry, 'delivery': delivery, 'question': question, 'asker': asker})
                    packet = json.dumps(p)
                    
                    # ---- SEND PACKET ONLY TO MK -------
                    mk_address = active_clients[active_clients.index("mk") + 1]
                    clients = ws.handler.server.clients.values()
                    for client in clients:
                        if client.address == mk_address:
                            client.ws.send(packet)
                
                    
        # a question came in
        if typ  == "question":
            
            question = message.get('data')
            type_of_inquiry = message.get('subtype')
            delivery = message.get('delivery')
            asker = message.get('username')
            cost = message.get('cost')
            
            # first, put the question in MK's queue
            key = datastore_client.key('MK_User', "mk")
            entity_in_question = datastore_client.get(key)
            archive = entity_in_question['archive']
            archive.append(type_of_inquiry)
            archive.append(delivery)
            archive.append(question)
            archive.append(asker)
            entity_in_question['archive'] = archive
            datastore_client.put(entity_in_question)
            
            #then, put the question in the user's 'outgoing' field and adjust the balance
            key = datastore_client.key('MK_User', asker)
            entity_in_question = datastore_client.get(key)
            og = entity_in_question['outgoing']
            
            full_question = str(type_of_inquiry) + ": " + str(question)
            og.append(full_question)
            
            og.append(delivery)
            
            full_cost = "Cost: $" + str(cost)
            og.append(full_cost)
            
            og.append("---------------")
            print(og)
            print(full_question)
            entity_in_question['outgoing'] = og
            b = entity_in_question['balance']
            b = b - cost
            entity_in_question['balance'] = float(round(b, 2))
            datastore_client.put(entity_in_question)
                
                  

        #A reply has come in from MK
        if typ == "archive":
            
            username = message.get('username')
            question = message.get('question')
            response = message.get('response')
            
            print("recieved an archive request for question",question)
            
            # archive the Q and A in the archive field for the user's Q and A History
            key = datastore_client.key('MK_User', username)
            entity_in_question = datastore_client.get(key)
            archive = entity_in_question['archive']
            archive.append(question)
            archive.append(response)
            archive.append("---------------")
            entity_in_question['archive'] = archive
            
            #then, delete the Q and related contents from the user's 'outgoing' field
            og = entity_in_question['outgoing']
            
            del og[og.index(question)+3] # delete the horizontal line
            del og[og.index(question)+2] # delete the cost
            del og[og.index(question)+1] # delete the delivery
            del og[og.index(question)]  # delete the Q
            
            entity_in_question['outgoing'] = og
            datastore_client.put(entity_in_question)
            
            #finally, make a notice appear on the user's homescreen
            p = dict({'type': 'update_yr_outgoing', 'username': username})
            packet = json.dumps(p)
                    
            # ---- SEND PACKET ONLY TO USER -------
            try:
                user_address = active_clients[active_clients.index(username) + 1]
                print(user_address," is the user's address")
                clients = ws.handler.server.clients.values()
                for client in clients:
                    if client.address == user_address:
                        client.ws.send(packet)
                        print("sent a packet")
            except:
                print("")
                
            #AT LAST, delete the Q and related contents from MK'S ARCHIVE (so it is seen as officially passed on)
            key = datastore_client.key('MK_User', "mk")
            entity_in_question = datastore_client.get(key)
            archive = entity_in_question['archive']
            
            trimmed_question = question.split(": ", 1)[1]
            
            del archive[archive.index(trimmed_question)-2] # delete the type of inquiry
            del archive[archive.index(trimmed_question)-1] # delete the delivery
            del archive[archive.index(trimmed_question)+1] # delete the asker
            del archive[archive.index(trimmed_question)]  # delete the Q   
            
            entity_in_question['archive'] = archive
            datastore_client.put(entity_in_question)
            
            
            
        if typ == "email":
            
            username = message.get('username')
            contents = message.get('contents')
            
            send_email('tod1106@yahoo.com', contents, username)   
                         
        
        print(active_clients)

# [END gae_flex_websockets_app]    



    













#-------------------------------------------------- Start of webpage hierarchy -----------------------------------------#
@app.before_request
def force_https():
    if request.endpoint in app.view_functions and request.headers.get('X-Forwarded-Proto', None) == 'http':
        return redirect(request.url.replace('http://', 'https://'))

@app.route('/my_story', methods=['GET', 'POST'])  
def my_story():
    return render_template('my_story.html')

@app.route('/reasons_to_choose', methods=['GET', 'POST']) 
def reasons_to_choose():
    return render_template('reasons_to_choose.html')

@app.route('/how_to_use', methods=['GET', 'POST'])
def how_to_use():
    return render_template('how_to_use.html')


@app.route('/', methods=['GET', 'POST'])
def index():
    
    if request.method == 'POST':
        if request.form['button'] == "Create an account":
            return redirect(url_for('create'))
        if request.form['button'] == "Login":
            return redirect(url_for('login'))
        
    return render_template('index.html')

@app.route('/create', methods=['GET', 'POST'])
def create():
    
    error = None
    if request.method == 'POST':
        session['username'] = request.form['username']
        password = request.form['password']
        
        # check if the username already exists.  If not, put it in the word file with the hashed password
        query = datastore_client.query(kind = 'MK_User')
        query.add_filter('username', '=', session['username'])
        results = list(query.fetch())
        if len(results) > 0:
            error = 'That username already exists.  Please choose another.'
        else:
            create_new_unap_entry(session['username'], password)   
            
            return redirect(url_for('home'))
        
    return render_template('create.html', error=error)
           
@app.route('/login', methods=['GET', 'POST'])
def login():#we put the username and balance in session variables in this step
    
    error = None
    if request.method == 'POST':

        key = datastore_client.key('MK_User', request.form['username'])
        print(key)
        entity_in_question = datastore_client.get(key)
        
        try:
            
            if (check_password_hash(entity_in_question['password'], request.form['password']) == True):
            
                session['balance'] = entity_in_question['balance']
                session['username'] = entity_in_question['username']
                flash(session['username'], category = 'message')
                
                return redirect(url_for('home'))
            else:
                error = 'Invalid Credentials.'
                
        except:
            
            error = "No such username exists."
        
    return render_template('login.html', error=error)


@app.route('/home', methods=['GET', 'POST'])
def home():
    
    error = None
    key = datastore_client.key('MK_User', session['username'])
    entity_in_question = datastore_client.get(key)
    session['balance'] = entity_in_question['balance']
    
    archive = entity_in_question['archive']
    archive_list = list(archive)
    og = entity_in_question['outgoing']
    og_list = list(og)
    
    if request.method == 'POST':
        
        key = datastore_client.key('MK_User', session['username'])
        entity_in_question = datastore_client.get(key)
        archive = entity_in_question['archive']
        
        workbook = xlsxwriter.Workbook("static/history.xlsx")
        worksheet = workbook.add_worksheet()
        
        cell = 1
        for s in range(2, len(archive), 3):
            a = archive[s].replace(",", "")
            q = archive[s-1].replace(",", "")
            
            question_cell = 'A' + str(cell)
            answer_cell = 'B' + str(cell)
            worksheet.write(question_cell, q)
            worksheet.write(answer_cell, a)
            cell += 1
            
        workbook.close()
        
        return send_from_directory("static/", "history.xlsx", as_attachment = True)
    
    return render_template('mk_home.html', pairs = archive_list, outgoing = og_list, key=stripe_keys['publishable_key'], error = error)


@app.route('/charge/<amt>', methods=['GET', 'POST'])
def charge(amt):
    
    if request.method == 'POST':
    
        customer = stripe.Customer.create(
            email=request.form['stripeEmail']
        )
        
        customer.sources.create(source=request.form['stripeToken'])
    
        charge = stripe.Charge.create(
            customer=customer.id,
            amount=amt,
            currency='usd',
            description='Translation'
        )
            
        error = None
        
        # get the entity in question from the database
        key = datastore_client.key('MK_User', session['username'])
        entity_in_question = datastore_client.get(key)
        
        # get the current balance, then add the money, and overwrite it
        pre_charge_balance = entity_in_question['balance']
        new_balance = float(round(pre_charge_balance, 2)) + (int(amt) / 100)
        entity_in_question['balance'] = float(round(new_balance, 2))
        
        session['balance'] = entity_in_question['balance']
        
        #get the archive and outgoing lists for display purposes on the homepage
        archive = entity_in_question['archive']
        archive_list = list(archive)
        og = entity_in_question['outgoing']
        og_list = list(og)
        
        #re-save the entity
        datastore_client.put(entity_in_question)
    
        return render_template('mk_home.html', pairs = archive_list, outgoing = og_list, key=stripe_keys['publishable_key'], error = error)
    

    
if __name__ == '__main__':
    print("""
This can not be run directly because the Flask development server does not
support web sockets. Instead, use gunicorn:
gunicorn -b 127.0.0.1:8080 -k flask_sockets.worker main:app
""")