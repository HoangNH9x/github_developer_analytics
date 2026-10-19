day_so = [9, 59, 21, 9, 20, 23, 19, 12, 19, 77]
# sap xep day so tang dan
day_so.sort()
print(day_so)

# xuat so nho nhat ra man hinh
print(day_so[0])


#tinh trung binh chia het cho 3
tong = 0
diem = 0
for n in day_so:
    if n % 3 == 0:
        tong = tong + n
        diem = diem + 1
TB = tong / diem
print("Trung binh chia het cho 3 la:", TB)