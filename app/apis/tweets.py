from flask_restx import Namespace, Resource, fields
from flask import abort, request
from app.models import Tweet, User
from app import db, login_manager

api = Namespace('tweets')

class JsonUser(fields.Raw):
    def format(self, value):
        return {
            'username': value.username,
            'email': value.email
        }

json_tweet = api.model('Tweet', {
    'id': fields.Integer,
    'text': fields.String,
    'created_at': fields.DateTime,
    'user': JsonUser
})

json_new_tweet = api.model('New tweet', {
    'text': fields.String(required=True)
})

@api.route('/<int:id>')
@api.response(404, 'Tweet not found')
@api.param('id', 'The tweet unique identifier')
class TweetResource(Resource):
    @api.marshal_with(json_tweet)
    def get(self, id):
        tweet = db.session.query(Tweet).get(id)
        if tweet is None:
            api.abort(404, "Tweet {} doesn't exist".format(id))
        else:
            return tweet

    @api.marshal_with(json_tweet, code=200)
    @api.expect(json_new_tweet, validate=True)
    def patch(self, id):
        user = load_user_from_request(request)
        if user is None:
            return api.abort(401, "api_key not valid")
        tweet = db.session.query(Tweet).get(id)
        if tweet is None:
            api.abort(404, "Tweet {} doesn't exist".format(id))
        else:
            if tweet.user_id != user.id:
                return api.abort(403, "Not allowed to update this tweet")
            tweet.text = api.payload["text"]
            db.session.commit()
            return tweet

    def delete(self, id):
        user = load_user_from_request(request)
        if user is None:
            return api.abort(401, "api_key not valid")
        tweet = db.session.query(Tweet).get(id)
        if tweet is None:
            api.abort(404, "Tweet {} doesn't exist".format(id))
        else:
            if tweet.user_id != user.id:
                return api.abort(403, "Not allowed to remove this tweet")
            db.session.delete(tweet)
            db.session.commit()
            return None

@api.route('')
class TweetsResource(Resource):
    @api.marshal_with(json_tweet, code=201)
    @api.expect(json_new_tweet, validate=True)
    @api.response(422, 'Invalid tweet')
    def post(self):
        user = load_user_from_request(request)
        if user is None:
            return api.abort(401, "api_key not valid")
        text = api.payload["text"]
        if len(text) > 0:
            tweet = Tweet(text=text)
            tweet.user_id = user.id
            db.session.add(tweet)
            db.session.commit()
            return tweet, 201
        else:
            return abort(422, "Tweet text can't be empty")

    @api.marshal_list_with(json_tweet)
    def get(self):
        tweets = db.session.query(Tweet).all()
        return tweets

@login_manager.request_loader
def load_user_from_request(request):
    api_key = request.headers.get('api_key')
    if api_key:
        user = db.session.query(User).filter_by(api_key=api_key).first()
        if user:
            return user
    return None
