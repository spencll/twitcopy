"""Message View tests."""

# run these tests like:
#
#    FLASK_ENV=production python -m unittest test_message_views.py


import os
from unittest import TestCase

from models import db, connect_db, Message, User, Likes

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

class UserModelTestCase(TestCase):
    """Test views for messages."""
    def setUp(self):
        with app.app_context():
            """Create test client, add sample data."""
            db.drop_all()
            db.create_all()

            # Unique identifier 
            self.uid = 94566
            # test user
            u = User.signup("testing", "testing@test.com", "password", None)
            u.id = self.uid
            db.session.commit()

            # Storing test user info
            self.u = User.query.get(self.uid)

            # Flask test client for requests
            self.client = app.test_client()

    def tearDown(self):
        with app.app_context():
            # Resets after the test 
            res = super().tearDown()
            db.session.rollback()
            return res

    def test_message_model(self):
        """Does basic model work?"""
        with app.app_context():
            m = Message(
                text="a warble",
                user_id=self.uid
            )

            db.session.add(m)
            db.session.commit()

            # Refreshing the user to avoid detached instance error
            self.u = User.query.get(self.u.id)

            # User should have 1 message and read "a warble"
            self.assertEqual(len(self.u.messages), 1)
            self.assertEqual(self.u.messages[0].text, "a warble")

    def test_message_likes(self):
        with app.app_context():
            m1 = Message(
                text="a warble",
                user_id=self.uid
            )

            m2 = Message(
                text="a very interesting warble",
                user_id=self.uid 
            )

            # Adding two messages and second user
            u = User.signup("yetanothertest", "t@email.com", "password", None)
            uid = 888
            u.id = uid
            db.session.add_all([m1, m2, u])
            db.session.commit()

            # "New user liking first message of test user"
            u.likes.append(m1)
            db.session.commit()

            # Getting the specific like of the new user
            l = Likes.query.filter(Likes.user_id == uid).all()
            self.assertEqual(len(l), 1)
            self.assertEqual(l[0].message_id, m1.id)


