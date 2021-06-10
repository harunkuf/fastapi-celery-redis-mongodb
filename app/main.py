import pymongo
from pymongo import MongoClient
from fastapi import FastAPI, Path
from typing import Optional
from pydantic import BaseModel
from worker import celery
import json

with open('cluster_password.txt', 'r') as file:
    cluster_password = file.read()

cluster = MongoClient(cluster_password)

db = cluster["b2metric"]
collection = db["library"]
user_db = db["user_database"]

app = FastAPI()

class Book(BaseModel):
	ISBN: int
	book_name: str
	publisher: str
	number_of_pages: Optional[int] = None
	author: str

class User(BaseModel):
	firstname: str
	lastname: str
	age: Optional[int] = None
	username: str
	password: str

def checkuser(username:str,password:str):
	"""
	Check user
	"""
	check_user = user_db.find_one({"username":username})

	if check_user is not None:
		if check_user["password"] == password:
			return "User Permitted"
		else:
			return "Wrong Password. Please Try again."
	else:
		return "No user by the username {}!".format(username)

def generate_book_id():
	for x in range(200000,500000):
		if collection.find_one({"_id":x}) is None:
			return x

@app.get("/")
def home():
	return "go to /docs"

@app.post("/Sign-Up")
def sign_up(user1:User):
	user1 = dict(user1)
	if user_db.find_one({"username":user1["username"]}) is not None:
		return "Username is taken!"

	user_db.insert_one(user1)

	return "Welcome to the library {}!".format(user1["username"])

@app.post("/Delete-User")
def delete_user(username:str,password:str):
	validation_results = checkuser(username,password)
	if validation_results != "User Permitted":
		return validation_results

	user_db.delete_one({"username":username})

	return "Account deleted."

@app.post("/check-status-of-book")
def check_status_of_book(id:int):
	requested_book = collection.find_one({"_id": id})

	return requested_book["status"]

@app.post("/add-new-book")
def add_new_book(username:str,password:str,book:Book):
	validation_results = checkuser(username,password)
	if validation_results != "User Permitted":
		return validation_results

	book_id = generate_book_id()

	book = dict(book)
	book["_id"] = book_id
	book["status"] = "in inventory"
	collection.insert_one(book)

	return "Your books ID is: {}. PLEASE TAKE NOTE OF YOUR BOOKS ID IN ORDER TO RETURN IT!".format(book_id)


@app.post("/borrow-book")
def borrow_book(username:str,password:str,book_name:Optional[str] = None, book_id: Optional[int] = None):
	"""
	Check user
	"""
	validation_results = checkuser(username,password)
	if validation_results != "User Permitted":
		return validation_results


	"""
	Check book
	"""
	if book_name is None and book_id is None:
		return "Please specify a Book Name or a Book ID"

	elif book_name is not None and book_id is not None:
		return "Please enter only Book Name or Book ID"
	elif book_name is not None and book_id is None:
		requested_book = collection.find_one({"book_name":book_name})

		if requested_book["status"] != "borrowed":
			if requested_book is not None:
				collection.update_one({"_id":requested_book["_id"]},{"$set":{"status":"borrowed"}})
				return "Book with id {}, named {}, by author {}, publisher {} is borrowed./n PLEASE TAKE NOTE OF YOUR BOOKS ID IN ORDER TO RETURN IT!".format(requested_book["_id"],
																									requested_book["book_name"],
																									requested_book["author"],
																									requested_book["publisher"])
		elif requested_book is None:
			return "No book named {} in inventory".format(book_name)

		else:
			return "You cannot borrow this book because it has already been borrowed by someone."

	elif book_name is None and book_id is not None:
		requested_book = collection.find_one({"_id":book_id})

		if requested_book["status"] != "borrowed":
			if requested_book is not None:
				collection.update_one({"_id":requested_book["_id"]},{"$set":{"status":"borrowed"}})
				return "Book with id {}, named {}, by author {}, publisher {} is borrowed./n PLEASE TAKE NOTE OF YOUR BOOKS ID IN ORDER TO RETURN IT!".format(requested_book["_id"],
																									requested_book["book_name"],
																									requested_book["author"],
																									requested_book["publisher"])
		elif requested_book is None:
			return "No book named {} in inventory".format(book_name)

		else:
			return "You cannot borrow this book because it has already been borrowed by someone."

@app.post("/return-book")
def return_book(username:str,password:str,id:int):
	"""
	Check user
	"""
	validation_results = checkuser(username,password)
	if validation_results != "User Permitted":
		return validation_results


	# Return book
	returned_book = collection.find_one({"_id":id})
	if returned_book is not None:
		if returned_book["status"] == "borrowed":
			collection.update_one({"_id":returned_book["_id"]},{"$set":{"status":"in inventory"}})
			return "Book with id {}, named {}, by author {}, publisher {} is returned".format(returned_book["_id"],
																							returned_book["book_name"],
																							returned_book["author"],
																							returned_book["publisher"])

		else:
			return "Book with id: {} is already in inventory!".format(id)

	else:
		return "No book with id: {} in database. Please use 'Add-Book method to add a new book to the database'".format(id)

@app.post("/borrow-many")
async def borrow_many(username:str,password:str,amount):
	validation_results = checkuser(username,password)
	if validation_results != "User Permitted":
		return validation_results

	task_name = "borrow.many"
	task = celery.send_task(task_name, args=[amount])
	return "Your task ID is: <" + task.id + "> Your task is being processed. You can check the status of your by using the check_task function at the bottom of the page. You can also check the status of your task using this link localhost:5000/check_task/{}".format(task.id)

@app.post("/return_all")
def return_all(username:str,password:str):
	validation_results = checkuser(username,password)
	if validation_results != "User Permitted":
		return validation_results

	collection.update_many({} ,{"$set":{"status":"in inventory"}})

	return "All books have been returned. Thank You!"


@app.get("/check_task/{id}")
def check_task(id: str):
    task = celery.AsyncResult(id)
    if task.state == 'SUCCESS':
        response = {
            'status': task.state,
            'result': task.result,
            'task_id': id
        }
    elif task.state == 'FAILURE':
        response = json.loads(task.backend.get(task.backend.get_key_for_task(task.id)).decode('utf-8'))
        del response['children']
        del response['traceback']
    else:
        response = {
            'status': task.state,
            'result': task.info,
            'task_id': id
        }
    return response