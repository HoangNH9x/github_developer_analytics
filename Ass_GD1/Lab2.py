import math

text = """Kiếp con người mỏng manh như là gió
Sống trên đời có được mấy lần vui
Sao phải đau mà không thể mỉm cười
Gắng buông nỗi ngậm ngùi nơi quá khứ

Nếu có thể sao ta không làm thử
Để tâm hồn khắc hai chữ bình an
Cho đôi chân bước thanh thản nhẹ nhàng
Dù hướng đời có muôn ngàn đá sỏi"""

print(text)

print("con người" in text)

d1 = 'Kiếp con người mỏng manh như là gió'
ket_qua = d1[4:14]
print(ket_qua.upper())


print("Phuong trinh bac 1: ax + b = 0")

a = float(input("Nhap a: "))
b = float(input("Nhap b: "))

if a == 0:
    if b == 0:
        print("Phuong trinh vo so nghiem")
    else:
        print("Phuong trinh vo nghiem")
else:
    x = -b / a
    print("Phuong trinh co nghiem la:", x)


print("Phuong trinh bac 2: ax^2 + bx + c = 0")

a = float(input("Nhap a: "))
b = float(input("Nhap b: "))
c = float(input("Nhap c: "))

delta = b**2 - 4* a*c
if delta < 0:
    print("Phuong trinh vo nghiem")
elif delta == 0:
    x = -b / 2*a
    print("Phuong trinh co nghiem kep la:", x)
else:
    x1 = (-b + math.sqrt(delta))/ (2*a)
    x2 = (-b - math.sqrt(delta)) / (2*a)
    print("x1 =", x1)
    print("x2 =",x2)
