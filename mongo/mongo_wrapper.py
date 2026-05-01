import pymongo
from config import Config
from bson.objectid import ObjectId
import datetime


class MongoWrapper:
    def __init__(self):
        config = Config()
        self.db = config.connect_to_db()

    # Add a new assignment into database
    # _id : ObjectID, generated automatically
    # user_email : String, associates assignment with user
    # title : String
    # course : String
    # description : String
    # due_date : datetime
    # estimated_hours : int
    # difficulty : int (1-5)
    # priority : String (low, medium, high)
    # status : String (overdue, due_soon, upcoming, completed)
    # completed : boolean (default false)
    # Returns the id of the newly created assignment as a string
    def add_assignment(
        self,
        user_email,
        title,
        course,
        description,
        due_date,
        estimated_hours,
        difficulty,
        priority,
        status,
        completed=False,
    ):
        doc = {
            "user_email": user_email,
            "title": title,
            "course": course,
            "description": description,
            "due_date": due_date,
            "estimated_hours": estimated_hours,
            "difficulty": difficulty,
            "priority": priority,
            "status": status,
            "completed": completed,
            "created_at": datetime.datetime.now(datetime.timezone.utc),
            "updated_at": datetime.datetime.now(datetime.timezone.utc),
        }

        result = self.db.assignments.insert_one(doc)
        return str(result.inserted_id)

    # Find assignments
    # user_email : String, the user to find assignments for
    # view : string with the value day/week/month
    # date : dateTime , optional, only include if viewing from the past/future, defaults to current
    # course : String, optional, only include if searching for a specific course
    # returns a list of assignment docs due today, this week, or this month/from the provided date
    def view_assignments(self, user_email, view, date=None, course=None):
        if date == None:
            day = datetime.datetime.now(datetime.timezone.utc)
        elif isinstance(date, datetime.datetime):
            day = date

        if view == "day":
            # Set start to beginning of day, end to beginning of next day
            start = day.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + datetime.timedelta(days=1)
        elif view == "week":
            # Set start to beginning of week, end to beginning of next week
            start = day - datetime.timedelta(days=day.weekday())
            start = start.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + datetime.timedelta(days=7)
        elif view == "month":
            # Set start to beginning of month, end to beginning of next month, adding 32 days guarantees the end is next month
            start = day.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end = (start + datetime.timedelta(days=32)).replace(day=1)

        if course == None:
            assignments = list(
                self.db.assignments.find(
                    {"user-email": user_email, "due_date": {"$gte": start, "$lt": end}}
                )
            )
        else:
            assignments = list(
                self.db.assignments.find(
                    {
                        "user-email": user_email,
                        "course": course,
                        "due_date": {"$gte": start, "$lt": end},
                    }
                )
            )

        return assignments

    # Mark assignment completed by id
    # _id : String, it's converted to ObjectId in the function
    # If sending get_assignment_id, _id possibly is None, in which case returns ValueError
    # Returns nothing on success, ValueError on failure
    def mark_completed(self, _id):
        if _id == None:
            return ValueError("Invalid value for _id parameter")
        elif not ObjectId.is_valid(_id):
            return ValueError("Invalid ObjectID")

        _id = ObjectId(_id)

        self.db.assignments.update_one(
            {"_id": ObjectId(_id)},
            {
                "$set": {
                    "completed": True,
                    "status": "completed",
                    "updated_at": datetime.datetime.now(datetime.timezone.utc),
                }
            },
        )

    # Get list of assignments with provided status, or ValueError if status invalid
    # user_email : String, the user to find assignments for
    # status : String (overdue, due_soon, upcoming, completed)
    # Use for status tracker
    def get_assignments_by_status(self, user_email, status):
        if status not in ["overdue", "due_soon", "upcoming", "completed"]:
            raise ValueError("Invalid value for status parameter")

        assignments = list(
            self.db.assignments.find({"user-email": user_email, "status": status})
        )
        return assignments

    # Get assignment id by title and course
    # user_email : String, the user to find assignment id for
    # Used to send into other methods mostly
    # Return: String id / None if not found
    def get_assignment_id(self, user_email, title, course):
        assignment = self.db.assignments.find_one(
            {"user-email": user_email, "title": title, "course": course}
        )

        if assignment:
            return str(assignment["_id"])
        else:
            return None
