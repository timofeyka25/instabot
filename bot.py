from instagrapi import Client
from random import choice, randint
from json import dumps, load
from datetime import datetime
from time import sleep
from queue import Queue


class Bot:
    def __init__(self):
        # init API Client
        self.client = Client()
        # var for display pause mode
        self.pause = False
        # counter of put likes in one session
        self.likes = 0
        # counter of put likes in one hour of running
        self.hour_likes = 0
        # time when was started app
        self.start_time = datetime.now()
        # time for one hour checking
        self.hour_time = datetime.now()
        # data structure for keeping users id
        self.queue = Queue()
        # required data which load from json file
        self.data = self.load_data()
        # account username
        self.username = None

    def load_data(self):
        """Loading required data from json file"""
        try:
            json_file = open("internal_files/data.json")
            if len(json_file.readlines()) != 0:
                json_file.seek(0)
                data = load(json_file)
                json_file.close()
                print("data", data)
                return data
            self.log("Error: data file is empty")
            exit(-3)
        except FileNotFoundError:
            open("internal_files/data.json", "w").close()
            self.log("Error: data file not found")
            exit(-2)

    def update_data(self):
        """Rewriting data in the file"""
        with open("internal_files/data.json", "w") as json_file:
            json_object = dumps(self.data)
            json_file.write(json_object)

    def get_username(self):
        """Getting account username"""
        self.username = self.client.username

    def update_users_queue(self, lst=None):
        """Generating a list of new user ids if users file is empty, else adding ids to the queue"""
        if lst is None:
            self.get_users_from_group()
        else:
            for user in lst:
                self.queue.put(user)
            self.log("The data has been uploaded from the file")

    def get_users_from_group(self):
        """Getting new users who are subscribed to a given group and removing group name from json data file"""
        if len(self.data['groups']) == 0:
            self.log("Error: list of groups is empty")
            return
        group = choice(self.data['groups'])
        users = self.client.user_followers(self.client.user_id_from_username(group), amount=20)
        if len(users):
            for key, value in users.items():
                if not value.is_private:
                    self.queue.put(key)
            self.log("The data in the queue has been updated")
        self.data['groups'].remove(group)
        self.update_data()
        self.log(f"Group {group} was removed from groups list. {len(self.data)} groups left.")
        self.save_users()

    def save_users(self):
        """Saving users to a file, mainly used before closing a session"""
        if not self.queue.empty():
            with open('internal_files/users.json', 'w') as fw:
                lst = []
                while not self.queue.empty():
                    lst.append(self.queue.get())
                for i in lst:
                    self.queue.put(i)
                json_object = dumps(lst)
                fw.write(json_object)
                self.log("The data was written into file")

    def update_users(self):
        """Reading a file with users and checking it"""
        lst = None
        try:
            with open('internal_files/users.json', 'r') as fr:
                if len(fr.readlines()) != 0:
                    fr.seek(0)
                    lst = load(fr)
        except FileNotFoundError:
            open("internal_files/users.json", "w").close()
            self.log("Error: users file not found")
        self.update_users_queue(lst)

    def has_liked(self, media_likers):
        """Checking a media for likes from user"""
        for user in media_likers:
            if self.username == user.username:
                return True
        return False

    def like_by_user_id(self, user_id):
        """Getting media from user id"""
        medias = self.client.user_medias(user_id=user_id, amount=randint(1, 2))
        self.put_likes(medias=medias, location=None)

    def like_by_locations(self):
        """Getting media from location"""
        location = choice(self.data['locations'])
        medias = self.client.location_medias_recent(location, amount=10)
        self.put_likes(medias=medias, location=location)

    def put_likes(self, medias, location=None):
        """Liking media with checking time limits"""
        if len(medias):
            for media in medias:
                if not self.pause:
                    self.put_like(media=media, location=location)
                    self.check_limits()
                else:
                    self.log("Pause...")
                    while self.pause:
                        sleep(5)
                        self.check_limits()

    def like_group_followers(self):
        """Liking users media from queue with checking time limits"""
        self.update_users()
        counter = 0
        while not self.queue.empty() and counter < 20:
            if not self.pause:
                self.like_by_user_id(self.queue.get())
                self.check_limits()
            else:
                self.log("Pause...")
                while self.pause:
                    sleep(5)
                    self.check_limits()
            counter += 1

    def put_like(self, media, location=None):
        """Put one like if media hasn't like and print any output the appropriate logs"""
        if not self.has_liked(self.client.media_likers(media_id=media.id)):
            if self.client.media_like(media.id):
                self.likes += 1
                self.hour_likes += 1
                if location is not None:
                    self.log(
                        f"Liked image from profile: {media.user.username}, id: {media.id}, location: {location}, "
                        f"url: {media.thumbnail_url}")
                else:
                    self.log(
                        f"Liked image from user: {media.user.username}, id: {media.id}, url: {media.thumbnail_url}")
            random_time = randint(30, 100)
            self.log(f"Waiting {random_time} seconds...")
            sleep(random_time)

    @staticmethod
    def log(string, end_session=False):
        """Write log in a file"""
        with open("internal_files/logs.txt", 'a') as logs:
            logs.write(f'{string} [Datetime:{datetime.now()}]\n')
            if end_session:
                logs.write('\n')

    def check_limits(self):
        """Checking time limits and pause if necessary"""
        time = datetime.now() - self.hour_time
        if self.hour_likes >= self.data['hour_limit']:
            if time.total_seconds() < 3600 and not self.pause:
                self.pause = True
                self.log(f"Likes before pause: {self.hour_likes}, all likes: {self.likes}, "
                         f"time before pause: {datetime.now() - self.hour_time}")
            elif time.total_seconds() > 3600:
                self.pause = False
                self.hour_likes = 0
                self.hour_time = datetime.now()

    def login(self):
        """Signing into your account"""
        return self.client.login(self.data['login'], self.data['password'])

    def start(self):
        """Starting method"""
        if not self.login():
            self.log("Error: login error")
            exit(-1)
        self.get_username()
        self.log(f"\nLogin into account with username: {self.data['login']}")
        print(f"Login into account with username: {self.data['login']}")

    def logout(self):
        """Logging out and write summary logs"""
        self.save_users()
        self.log(f"\nLikes by session: {self.likes}, session time: {datetime.now() - self.start_time}")
        self.log(f"Logout from account with username: {self.data['login']}", end_session=True)
        print(f"Likes by session: {self.likes}, session time: {datetime.now() - self.start_time}\n" +
              f"Logout from account with username: {self.data['login']}")
        return self.client.logout()

    def run(self):
        """Method for run this app"""
        self.start()
        while self.likes < self.data['limit']:
            funcs = [self.like_group_followers, self.like_by_locations]
            choice(funcs)()
        else:
            self.logout()


bot = Bot()
bot.run()
