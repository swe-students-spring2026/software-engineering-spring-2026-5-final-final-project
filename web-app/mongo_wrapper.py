import os
import pymongo
import datetime
from bson.objectid import ObjectId
from config import Config
class MongoWrapper:
    def __init__(self):
        config = Config()
        self.db = config.connect_to_db()

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
                    {"user_email": user_email, "due_date": {"$gte": start, "$lt": end}}
                )
            )
        else:
            assignments = list(
                self.db.assignments.find(
                    {
                        "user_email": user_email,
                        "course": course,
                        "due_date": {"$gte": start, "$lt": end},
                    }
                )
            )

        return assignments

    # Get assignment id by title and course
    # user_email : String, the user to find assignment id for
    # Used to send into other methods mostly
    # Return: String id / None if not found
    def get_assignment_id(self, user_email, title, course):
        assignment = self.db.assignments.find_one(
            {"user_email": user_email, "title": title, "course": course}
        )

        if assignment:
            return str(assignment["_id"])
        else:
            return None
