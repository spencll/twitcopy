"""Message View tests."""

# run these tests like:
#
#    FLASK_ENV=production python -m unittest test_message_views.py

import os
from unittest import TestCase

from models import db, connect_db, Message, User

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "postgresql:///warbler-test"


# Now we can import app

from app import app, CURR_USER_KEY

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data
with app.app_context():
    db.create_all()

# Don't have WTForms use CSRF at all, since it's a pain to test

app.config['WTF_CSRF_ENABLED'] = False

class MessageViewTestCase(TestCase):
    """Test views for messages."""

    def setUp(self):
        """Create test client, add sample data."""
        with app.app_context():
            db.drop_all()
            db.create_all()

            # Flask test client for requests
            self.client = app.test_client()

            # Storing test user info 
            self.testuser = User.signup(username="testuser",
                                        email="test@test.com",
                                        password="testuser",
                                        image_url=None)
            self.testuser_id = 8989
            self.testuser.id = self.testuser_id
            db.session.add(self.testuser)
            db.session.commit()

    def test_add_message(self):
        """Can use add a message?"""
        with app.app_context():
            # Since we need to change the session to mimic logging in,
            # we need to use the changing-session trick:

            # making c the testing client 
            with self.client as c:
                # making sess the session of test client and then changing it to mimic login
                with c.session_transaction() as sess:
                     # Refreshing the user to avoid detached instance error
                    self.testuser = User.query.get(self.testuser_id)

                    sess[CURR_USER_KEY] = self.testuser.id

                # Now, that session setting is saved, so we can have
                # the rest of ours test

                # response of message post request 
                resp = c.post("/messages/new", data={"text": "Hello"})

                # Make sure it redirects
                self.assertEqual(resp.status_code, 302)

                # Getting the posted message and seeing if it's "Hello"
                msg = Message.query.one()
                self.assertEqual(msg.text, "Hello")

    def test_add_no_session(self):
        with app.app_context():
            with self.client as c:
                # Not logged in, no session set up 
                resp = c.post("/messages/new", data={"text": "Hello"}, follow_redirects=True)
                # Should give not authorized response 
                self.assertEqual(resp.status_code, 200)
                self.assertIn("Access unauthorized", str(resp.data))

    def test_add_invalid_user(self):
        with self.client as c:
            # Non existant user id in session "logged in"
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = 99222224 # user does not exist

            resp = c.post("/messages/new", data={"text": "Hello"}, follow_redirects=True)
            # Should give not authorized response 
            self.assertEqual(resp.status_code, 200)
            self.assertIn("Access unauthorized", str(resp.data))
    
    def test_message_show(self):
        with app.app_context():
            m = Message(
                id=1234,
                text="a test message",
                user_id=self.testuser_id
            )
            
            db.session.add(m)
            db.session.commit()

            # "Logged in"
            with self.client as c:
                with c.session_transaction() as sess:
                     # Refreshing the user to avoid detached instance error
                    self.testuser = User.query.get(self.testuser_id)
                    
                    sess[CURR_USER_KEY] = self.testuser.id
                
                # Getting message
                m = Message.query.get(1234)
                # Getting get response 
                resp = c.get(f'/messages/{m.id}')
                # response data = message text
                self.assertEqual(resp.status_code, 200)
                self.assertIn(m.text, str(resp.data))


    def test_invalid_message_show(self):
        with app.app_context():
            # "Logged in"
            with self.client as c:
                with c.session_transaction() as sess:
                    # Refreshing the user to avoid detached instance error
                    self.testuser = User.query.get(self.testuser_id)

                    sess[CURR_USER_KEY] = self.testuser.id
                
                # Getting get response
                resp = c.get('/messages/99999999')
                # Not found response code 
                self.assertEqual(resp.status_code, 404)

    def test_message_delete(self):
        with app.app_context():
            m = Message(
                id=1234,
                text="a test message",
                user_id=self.testuser_id
            )
            db.session.add(m)
            db.session.commit()

            # "Logged in"
            with self.client as c:
                with c.session_transaction() as sess:
                    # Refreshing the user to avoid detached instance error
                    self.testuser = User.query.get(self.testuser_id)
                    sess[CURR_USER_KEY] = self.testuser.id

                # Getting post response for deletion 
                resp = c.post("/messages/1234/delete", follow_redirects=True)
                self.assertEqual(resp.status_code, 200)
                # Specific message should be gone
                m = Message.query.get(1234)
                self.assertIsNone(m)

    def test_unauthorized_message_delete(self):
        with app.app_context():
            # A second user that will try to delete the message
            u = User.signup(username="unauthorized-user",
                            email="testtest@test.com",
                            password="password",
                            image_url=None)
            u.id = 76543

            #Message is owned by testuser
            m = Message(
                id=1234,    
                text="a test message",
                user_id=self.testuser_id
            )
            db.session.add_all([u, m])
            db.session.commit()
            # Logged in as second user
            with self.client as c:
                with c.session_transaction() as sess:
                    sess[CURR_USER_KEY] = 76543

                # Delete response should be not authorized 
                resp = c.post("/messages/1234/delete", follow_redirects=True)
                self.assertEqual(resp.status_code, 200)
                self.assertIn("Access unauthorized", str(resp.data))
                # Message should still be there 
                m = Message.query.get(1234)
                self.assertIsNotNone(m)

    def test_message_delete_no_authentication(self):
        with app.app_context():
            m = Message(
                id=1234,
                text="a test message",
                user_id=self.testuser_id
            )
            db.session.add(m)
            db.session.commit()

            # Trying to delete message without authorization 
            with self.client as c:
                resp = c.post("/messages/1234/delete", follow_redirects=True)
                self.assertEqual(resp.status_code, 200)
                self.assertIn("Access unauthorized", str(resp.data))
                #Message should still be there 
                m = Message.query.get(1234)
                self.assertIsNotNone(m)
