# list 版
pd_name = ["冰鎮檸檬紅茶-535ml", "冰鎮花果茶"]
pd_bd = ["4710095951502", "47110096961603", "4710946578193", "47155178466644717546061667"]
pd_price = [29, 35]
alcohol_name = ["再見南國-芒果風味"]
alchol_bd = ["4711588006747", ""]
alcohol_price = [140]
香菸_bd = ["47100535312345"]
香菸_name = ["尊爵香菸"]
香菸_price = [95]
total = 0

def 結帳():
    while True:    
        global total
        barcode = input("請輸入條碼-> ")

        if barcode.lower == "q":
            break

        if barcode in pd_bd:
            idx = pd_bd.index(barcode)
            money = pd_price[idx]
            total += money
            print(f"商品:{pd_name[idx]}", f"價格:{money}元", f"總額:{total}元")
        elif barcode in alchol_bd or barcode in 香菸_bd:
            if barcode in alchol_bd:
                idx = alchol_bd.index(barcode)
                name, money, age_limit = alcohol_name[idx], alcohol_price[idx], 18
            else:
                idx = 香菸_bd.index(barcode)
                name, money, age_limit = 香菸_name[idx], 香菸_price[idx], 20

            print(f"商品:{name}", f"此商品需確認是否年滿{age_limit}歲")
            age_check = int(input(f"是否{age_limit}歲(1=是/0=否)-> "))
            if not bool(age_check):
                print("抱歉，因未成年而無法購買")
            else:
                total += money
                print(f"商品:{name}", f"價格:{money}元", f"總額:{total}元")
        else:
            print("查無商品")
結帳()