import psycopg2

conn = psycopg2.connect(
    host="localhost",
    database="skillstake",
    user="user",
    password="password"
)

cur = conn.cursor()
cur.execute("SELECT * FROM quizzes;")
rows = cur.fetchall()
for row in rows:
    print(row)
cur.close()
conn.close()