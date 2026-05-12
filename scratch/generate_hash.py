import bcrypt

password = "Pass@1234"
pwd_bytes = password.encode("utf-8")[:72]
salt = bcrypt.gensalt()
hashed = bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")
print(hashed)
