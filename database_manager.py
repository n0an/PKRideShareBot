import sqlite3

# ==============================================
# ================== DB METHODS ================
# ==============================================
# DB create
db_filename = 'rides.db'
def create_db():
    conn = sqlite3.connect(db_filename)
    conn.close()

# CREATE TABLE
def create_db_table():
    with sqlite3.connect(db_filename) as conn:
        conn.execute("""
          CREATE TABLE ride (
            id            INT PRIMARY KEY,
            direction     TEXT,
            destination   TEXT,
            dateandtime   TEXT,
            passengers    INT,
            requests      INT,
            phonenumber   TEXT,
            user_id       INT,
            user_name     TEXT,
            createdat     TEXT
          );
        """)

# INSERT TO DB TABLE
def insert_to_db(ride_id, direction, destination, dateandtime, passengers, requests, phonenumber, user_id, user_name, createdat):
    with sqlite3.connect(db_filename) as conn:
        conn.execute("""
          INSERT INTO ride (id,
                           direction,
                           destination, 
                           dateandtime, 
                           passengers, 
                           requests,
                           phonenumber,
                           user_id,
                           user_name,
                           createdat)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (
            '{}'.format(ride_id),
            '{}'.format(direction),
            '{}'.format(destination),
            '{}'.format(dateandtime),
            '{}'.format(passengers),
            '{}'.format(requests),
            '{}'.format(phonenumber),
            '{}'.format(user_id),
            '{}'.format(user_name),
            '{}'.format(createdat)
            )
        )

# GET NOT MY RIDES FROM DB TABLE
def get_rides_from_table(user_id, direc):
    with sqlite3.connect(db_filename) as conn:
        conn.row_factory = sqlite3.Row

        params = (direc, user_id)

        cur = conn.cursor()
        cur.execute("SELECT * FROM ride WHERE direction=? AND user_id <> ?", params)

        suitable_rides = []

        for row in cur.fetchall():
            # print(row)
            id, directn, destination, dateandtime, passengers, requests, phonenumber, user_id, user_name, createdat = row

            ride = {}
            ride['ride_id'] = id
            ride['ride_direction'] = directn
            ride['ride_destination'] = destination
            ride['ride_datetime'] = dateandtime
            ride['ride_passengers'] = passengers
            ride['requests_rides'] = requests
            ride['user_phonenumber'] = phonenumber
            ride['user_id'] = user_id
            ride['user_name'] = user_name


            suitable_rides.append(ride)

        return suitable_rides

# GET MY RIDES FROM DB TABLE
def get_my_rides_from_table(user_id):
    with sqlite3.connect(db_filename) as conn:
        conn.row_factory = sqlite3.Row

        params = (user_id, )

        cur = conn.cursor()
        cur.execute("SELECT * FROM ride WHERE user_id = ?", params)

        suitable_rides = []

        for row in cur.fetchall():
            # print(row)
            id, directn, destination, dateandtime, passengers, requests, phonenumber, user_id, user_name, createdat = row

            ride = {}

            ride['ride_direction'] = directn
            ride['ride_destination'] = destination
            ride['ride_datetime'] = dateandtime
            ride['ride_passengers'] = passengers
            ride['requests_rides'] = requests
            ride['user_phonenumber'] = phonenumber
            ride['user_id'] = user_id
            ride['user_name'] = user_name

            suitable_rides.append(ride)

        return suitable_rides

# DELETE MY RIDES
def delete_my_rides_from_table(user_id):
    with sqlite3.connect(db_filename) as conn:

        params = (user_id,)

        cur = conn.cursor()
        cur.execute("DELETE FROM ride WHERE user_id = ?", params)


# GET MAX ID
def get_max_id_from_table():
    with sqlite3.connect(db_filename) as conn:
        cur = conn.cursor()
        cur.execute("SELECT max(id) FROM ride")

        (maximum_id,) = cur.fetchone()

        return maximum_id

# UPDATE REQUESTS COUNT FOR RIDE
def increment_requests_count(ride_id, new_requests_count):
    with sqlite3.connect(db_filename) as conn:
        cur = conn.cursor()
        cur.execute("UPDATE ride set requests=:requests WHERE id=:ride_id",
                    {'requests': new_requests_count, 'ride_id': ride_id})