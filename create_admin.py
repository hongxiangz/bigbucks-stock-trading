import hashlib
from model import *


if __name__ == '__main__':
    password = 'admin'
    new_user = User()
    new_user.username = 'admin'
    new_user.role = 'admin'
    new_user.balance = 0
    new_user.password = hashlib.md5(password.encode()).hexdigest()
    print(f'admin -> {new_user.password}')
    new_user.save()

