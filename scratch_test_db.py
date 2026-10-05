import sqlite3
import re

conn = sqlite3.connect('database/tnea.db')
c = conn.cursor()
c.execute("SELECT college_code, college_name FROM colleges WHERE lower(college_name) LIKE '%eshwar%' OR lower(college_name) LIKE '%eswar%'")
print("Eshwar/Eswar matches in colleges table:")
for row in c.fetchall():
    print(row)

c.execute("SELECT college_code, college_name FROM colleges WHERE lower(college_name) LIKE '%venkateshwara%' OR lower(college_name) LIKE '%venkateswara%'")
print("\nVenkateshwara matches in colleges table:")
for row in c.fetchall()[:5]:
    print(row)

conn.close()
