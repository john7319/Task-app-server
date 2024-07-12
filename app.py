#!/usr/bin/env python3
import os


from sqlite3 import IntegrityError

from models import db, Task, User, Assignment, bcrypt
from flask_migrate import Migrate
from flask import Flask, request, jsonify, session
from flask_restful import Api, Resource
from datetime import datetime
from flask_cors import CORS

from dotenv import load_dotenv
load_dotenv()


app = Flask(__name__)
app.secret_key = b'Y\xf1Xz\x00\xad|eQ\x80t \xca\x1a\x10K'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URI')
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.json.compact = False

migrate = Migrate(app, db)

db.init_app(app)

CORS(app)

api = Api(app)
bcrypt.init_app(app)


@app.route("/")
def index():
    return "<h1>Task Management App</h1>"

class CheckSession(Resource):
    def get(self):
        
        user_id = session['user_id']
        if user_id:
            user = User.query.filter(User.id == user_id).first()
            return user.to_dict(), 200
        
        return {}, 401

class Login(Resource):
    def post(self):

        request_json = request.get_json()

        email = request_json.get('email')
        password = request_json.get('password')

        user = User.query.filter(User.email == email).first()

        if user:
            if user.authenticate(password):

                session['user_id'] = user.id
                return user.to_dict(), 200

        return {'error': '401 Unauthorized'}, 401
    
class Logout(Resource):
    def delete(self):
        if session['user_id']:
            session['user_id'] = None
            return {}, 204
        return {'error': 'Unauthorized'}, 401

class UsersResource(Resource):
    def get(self):
        users = User.query.all()
        return [user.to_dict(only=('id', 'name', 'email')) for user in users], 200
        

    def post(self):
        data = request.get_json()
        try:
            new_user = User(
                name=data['name'],
                email=data['email'],
                password=data['password']
            )
            db.session.add(new_user)
            db.session.commit()
            return new_user.to_dict(), 201
        except Exception as e:
            db.session.rollback()
            return {"errors": [str(e)]}, 400

class UserResource(Resource):
    def get(self, id):
        user = db.session.get(User, id)
        if user:
            return user.to_dict(), 200
        return {"error": "User not found"}, 404

    def delete(self, id):
        user = db.session.get(User, id)
        if user:
            db.session.delete(user)
            db.session.commit()
            return '', 204
        return {"error": "User not found"}, 404

class TasksResource(Resource):
    def get(self):
        tasks = Task.query.all()
        return [task.to_dict(only=('id', 'title', 'description', 'due_date')) for task in tasks], 200

    def post(self):
        data = request.get_json()
        
            # Check if user_id is provided
        if 'user_id' not in data:
            return jsonify({"error": "user_id is required"}), 400

        user_id = data['user_id']

        # Check if the provided user_id corresponds to an existing user
        user = User.query.get(user_id)
        if user is None:
            return jsonify({"error": "Invalid user_id"}), 400
        try:
            new_task = Task(
                title=data['title'],
                description=data['description'],
                due_date=datetime.strptime(data['due_date'], '%Y-%m-%d').date(),
                user_id=user_id
            )
            db.session.add(new_task)
            db.session.commit()
            return new_task.to_dict(), 201
        except Exception as e:
            db.session.rollback()
            return {"errors": [str(e)]}, 400

class TaskResource(Resource):
    def get(self, id):
        task = db.session.get(Task, id)
        if task:
            return task.to_dict(), 200
        return {"error": "Task not found"}, 404

    def patch(self, id):
        task = db.session.get(Task, id)
        if task:
            data = request.get_json()
            task.title = data.get('title', task.title)
            task.description = data.get('description', task.description)
            task.due_date = data.get('due_date', task.due_date)
            db.session.commit()
            return task.to_dict(), 200
        return {"error": "Task not found"}, 404

    def delete(self, id):
        try:
            task = db.session.query(Task).get(id)
            if task:
                for assignment in task.assignments:
                    db.session.delete(assignment)
                db.session.delete(task)
                db.session.commit()
                return '', 204
            return {"error": "Task not found"}, 404
        except IntegrityError as e:
            db.session.rollback()
            return {"error": "Integrity error occurred while deleting task"}, 500
        except Exception as e:
            db.session.rollback()
            return {"error": f"An error occurred while deleting task: {str(e)}"}, 500

class AssignmentsResource(Resource):
    def get(self):
        assignments = Assignment.query.all()
        return [assignment.to_dict(only=('id', 'task_id', 'user_id', 'status')) for assignment in assignments], 200

    def post(self):
        data = request.get_json()
        try:
            new_assignment = Assignment(
                task_id=data['task_id'],
                user_id=data['user_id'],
                status=data['status']
            )
            db.session.add(new_assignment)
            db.session.commit()
            return new_assignment.to_dict(), 201
        except Exception as e:
            db.session.rollback()
            return {"errors": [str(e)]}, 400
api.add_resource(CheckSession, '/check_session', endpoint='check_session')
api.add_resource(Login, '/login', endpoint='login')
api.add_resource(Logout, '/logout', endpoint='logout')
api.add_resource(UsersResource, '/users')
api.add_resource(UserResource, '/users/<int:id>')   
api.add_resource(TasksResource, '/tasks')
api.add_resource(TaskResource, '/tasks/<int:id>')
api.add_resource(AssignmentsResource, '/assignments')

if __name__ == "__main__":
    app.run(debug=True)