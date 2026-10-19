import re

phone = input("Nhap so dien thoai: ")

pattern = r"0\d{9}"

if re.fullmatch(pattern,phone):
    print("So dien thoai hop le!")
else :
    print("So dien thoai khong hop le!")


