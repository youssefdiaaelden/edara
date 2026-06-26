# ================== IMPORTS ==================
from ai_model import predict_top_products, predict_profit
from datetime import datetime
from functools import partial
import sys
import sqlite3
import winsound
from PySide6.QtWidgets import QSpinBox
from services.sales_service import SalesService
from cashier import  print_receipt

from PySide6.QtCore import Qt

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem,
    QLabel, QDialog, QFormLayout, QGridLayout, QHeaderView
)


# ================== ADD PRODUCT ==================
class AddProductDialog(QDialog):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Add Product")

        layout = QFormLayout()

        self.name = QLineEdit()
        self.barcode = QLineEdit()
        self.cost = QLineEdit()
        self.profit = QLineEdit()
        self.qty = QLineEdit()

        layout.addRow("Name:", self.name)
        layout.addRow("Barcode:", self.barcode)
        layout.addRow("Cost:", self.cost)
        layout.addRow("Profit:", self.profit)
        layout.addRow("Quantity:", self.qty)

        self.barcode.setFocus()
        self.barcode.returnPressed.connect(self.fill_product_data)

        btn = QPushButton("Save")
        btn.clicked.connect(self.save_product)

        layout.addWidget(btn)
        self.setLayout(layout)

    def fill_product_data(self):

        barcode = self.barcode.text()

        conn = sqlite3.connect("database/store.db")
        cursor = conn.cursor()

        cursor.execute("""
        SELECT name, cost_price, profit_margin, quantity
        FROM products
        WHERE barcode=?
        """, (barcode,))

        product = cursor.fetchone()

        conn.close()

        if product:

            name, cost, profit, qty = product

            self.name.setText(name)
            self.cost.setText(str(cost))
            self.profit.setText(str(profit))
            self.qty.setText("1")

        else:
            self.name.setFocus()

    def save_product(self):

        try:
            try:
                cost = float(self.cost.text())
            except:
                return
            profit = float(self.profit.text())
            qty = int(self.qty.text())

        except:
            print("❌ Invalid Input")
            return

        barcode = self.barcode.text()

        conn = sqlite3.connect("database/store.db")
        cursor = conn.cursor()

        cursor.execute("""
        SELECT id, quantity
        FROM products
        WHERE barcode=?
        """, (barcode,))

        existing = cursor.fetchone()

        sell_price = cost + profit

        if existing:

            product_id, old_qty = existing

            cursor.execute("""
            UPDATE products
            SET
                name=?,
                cost_price=?,
                sell_price=?,
                profit_margin=?,
                quantity=?
            WHERE id=?
            """, (
                self.name.text(),
                cost,
                sell_price,
                profit,
                old_qty + qty,
                product_id
            ))

        else:

            cursor.execute("""
            INSERT INTO products
            (name, barcode, cost_price, sell_price, profit_margin, quantity)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (
                self.name.text(),
                barcode,
                cost,
                sell_price,
                profit,
                qty
            ))

        conn.commit()
        conn.close()

        self.accept()


# ================== EDIT PRODUCT ==================
class EditProductDialog(QDialog):
    def __init__(self, product):
        super().__init__()

        self.product = product

        self.setWindowTitle("Edit Product")
        self.resize(350, 250)

        layout = QFormLayout()

        self.name = QLineEdit()
        self.barcode = QLineEdit()
        self.cost = QLineEdit()
        self.profit = QLineEdit()
        self.qty = QLineEdit()

        layout.addRow("Name:", self.name)
        layout.addRow("Barcode:", self.barcode)
        layout.addRow("Cost:", self.cost)
        layout.addRow("Profit:", self.profit)
        layout.addRow("Quantity:", self.qty)

        product_id, name, sell_price, quantity = product

        conn = sqlite3.connect("database/store.db")
        cursor = conn.cursor()

        cursor.execute("""
        SELECT barcode, cost_price, profit_margin
        FROM products
        WHERE id=?
        """, (product_id,))

        extra = cursor.fetchone()

        conn.close()

        barcode, cost, profit = extra

        self.name.setText(name)
        self.barcode.setText(barcode)
        self.cost.setText(str(cost))
        self.profit.setText(str(profit))
        self.qty.setText(str(quantity))

        save_btn = QPushButton("Save Changes")
        save_btn.clicked.connect(self.save_changes)

        delete_btn = QPushButton("Delete Product")
        delete_btn.setStyleSheet("background-color:red;")
        delete_btn.clicked.connect(self.delete_product)

        layout.addWidget(save_btn)
        layout.addWidget(delete_btn)

        self.setLayout(layout)

    def save_changes(self):

        product_id = self.product[0]

        try:
            try:
                cost = float(self.cost.text())
            except:
                return
            profit = float(self.profit.text())
            qty = int(self.qty.text())

        except:
            print("❌ Invalid Input")
            return

        conn = sqlite3.connect("database/store.db")
        cursor = conn.cursor()

        cursor.execute("""
        SELECT id
        FROM products
        WHERE barcode=? AND id!=?
        """, (
            self.barcode.text(),
            product_id
        ))

        exists = cursor.fetchone()

        if exists:
            print("❌ Barcode already exists")
            conn.close()
            return

        sell_price = cost + profit

        cursor.execute("""
        UPDATE products
        SET
            name=?,
            barcode=?,
            cost_price=?,
            profit_margin=?,
            sell_price=?,
            quantity=?
        WHERE id=?
        """, (
            self.name.text(),
            self.barcode.text(),
            cost,
            profit,
            sell_price,
            qty,
            product_id
        ))

        conn.commit()
        conn.close()

        self.accept()

    def delete_product(self):

        product_id = self.product[0]

        conn = sqlite3.connect("database/store.db")
        cursor = conn.cursor()

        cursor.execute("""
        DELETE FROM products
        WHERE id=?
        """, (product_id,))

        conn.commit()
        conn.close()

        self.accept()


# ================== INVENTORY ==================
class InventoryDialog(QDialog):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Inventory")
        self.resize(850, 500)

        layout = QVBoxLayout()

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search name or barcode...")
        self.search.textChanged.connect(self.load_products)

        layout.addWidget(self.search)

        self.table = QTableWidget()

        self.table.setColumnCount(6)

        self.table.setHorizontalHeaderLabels([
            "ID",
            "Name",
            "Price",
            "Qty",
            "+Qty",
            "Edit"
        ])

        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        layout.addWidget(self.table)

        self.setLayout(layout)

        self.load_products()

    def load_products(self):

        conn = sqlite3.connect("database/store.db")
        cursor = conn.cursor()

        search = self.search.text()

        cursor.execute("""
        SELECT id, name, sell_price, quantity
        FROM products
        WHERE name LIKE ? OR barcode LIKE ?
        ORDER BY id DESC
        """, (
            f"%{search}%",
            f"%{search}%"
        ))

        products = cursor.fetchall()

        self.table.setRowCount(0)

        for row_idx, product in enumerate(products):

            self.table.insertRow(row_idx)

            for col_idx, value in enumerate(product):

                item = QTableWidgetItem(str(value))

                if col_idx == 3:

                    qty = int(value)

                    if qty <= 5:
                        item.setBackground(Qt.red)

                    elif qty <= 10:
                        item.setBackground(Qt.yellow)

                self.table.setItem(row_idx, col_idx, item)

            qty_btn = QPushButton("+10 Qty")
            qty_btn.clicked.connect(partial(self.add_qty, product))

            self.table.setCellWidget(row_idx, 4, qty_btn)

            edit_btn = QPushButton("Edit")
            edit_btn.clicked.connect(partial(self.open_edit_dialog, product))

            self.table.setCellWidget(row_idx, 5, edit_btn)

        conn.close()

    def add_qty(self, product):

        product_id, name, price, qty = product

        conn = sqlite3.connect("database/store.db")
        cursor = conn.cursor()

        cursor.execute("""
        UPDATE products
        SET quantity=?
        WHERE id=?
        """, (
            qty + 10,
            product_id
        ))

        conn.commit()
        conn.close()

        self.load_products()

    def open_edit_dialog(self, product):

        dialog = EditProductDialog(product)

        if dialog.exec():
            self.load_products()


# ================== DASHBOARD ==================
class DashboardDialog(QDialog):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("dashboard")

        layout = QVBoxLayout()

        self.label = QLabel()

        layout.addWidget(self.label)

        self.setLayout(layout)

        self.load_data()

    def load_data(self):

        conn = sqlite3.connect("database/store.db")
        cursor = conn.cursor()

        cursor.execute("SELECT SUM(total_price) FROM sales")

        total_sales = cursor.fetchone()[0] or 0

        cursor.execute("SELECT SUM(total_price) FROM sales_items")

        total_revenue = cursor.fetchone()[0] or 0

        profit = total_sales - (total_revenue * 0.7)

        top_pred = predict_top_products()
        profit_pred = predict_profit()

        if hasattr(top_pred, "iterrows") and len(top_pred) > 0:

            top_text = "\n".join([
                f"{row['product_name']} ({row['quantity']})"
                for _, row in top_pred.iterrows()
            ])

        else:
            top_text = "No data"

        self.label.setText(f"""
💰 Total Sales: {total_sales} EGP

📈 Profit: {round(profit, 2)} EGP

🤖 Predicted Top Products:
{top_text}

🤖 Expected Profit:
{profit_pred}
""")

        conn.close()


# ================== REPORTS ==================
class ReportsDialog(QDialog):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Reports")

        layout = QVBoxLayout()

        self.label = QLabel()

        layout.addWidget(self.label)

        self.setLayout(layout)

        self.load_reports()

    def load_reports(self):

        conn = sqlite3.connect("database/store.db")
        cursor = conn.cursor()

        cursor.execute("SELECT SUM(total_price) FROM sales")

        total_sales = cursor.fetchone()[0] or 0

        cursor.execute("""
        SELECT product_name, SUM(quantity)
        FROM sales_items
        GROUP BY product_name
        ORDER BY SUM(quantity) DESC
        LIMIT 3
        """)

        top_products = cursor.fetchall()

        text = f"💰 Total Sales: {total_sales}\n\n"

        text += "🏆 Top Products:\n"

        for p in top_products:
            text += f"{p[0]} ({p[1]})\n"

        self.label.setText(text)

        conn.close()


# ================== LOGIN ==================
class LoginWindow(QDialog):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Login")

        layout = QFormLayout()

        self.username = QLineEdit()

        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)

        layout.addRow("Username:", self.username)
        layout.addRow("Password:", self.password)

        btn = QPushButton("Login")
        btn.clicked.connect(self.handle_login)

        layout.addWidget(btn)

        self.setLayout(layout)

        self.role = None
        self.username_value = None

    def handle_login(self):

        from auth import login

        role = login(
            self.username.text(),
            self.password.text()
        )

        if role:
            self.username_value = self.username.text()
            self.role = role
            self.accept()

        else:

            self.username.clear()
            self.password.clear()

            print("❌ Wrong Login")


# ================== MAIN APP ==================
class CashierApp(QWidget):
    def __init__(self, role, username):
        super().__init__()

        self.role = role
        self.username = username

        self.setWindowTitle("Store System Pro")
        self.resize(1000, 600)

        self.cart = []

        self.setStyleSheet("""
        QWidget {
            background-color: #1e1e2f;
            color: white;
        }
        """)

        main_layout = QHBoxLayout()

        left_layout = QVBoxLayout()
        right_layout = QVBoxLayout()

        # ================== BARCODE ==================
        self.barcode_input = QLineEdit()

        self.barcode_input.setPlaceholderText("Scan Barcode...")

        self.barcode_input.returnPressed.connect(self.add_product)

        left_layout.addWidget(self.barcode_input)

        # ================== TABLE ==================
        self.table = QTableWidget(0, 5)

        self.table.setHorizontalHeaderLabels([
            "Product",
            "Qty",
            "Price",
            "Total",
            "Delete"
        ])

        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        left_layout.addWidget(self.table)

        # ================== TOTAL ==================
        self.total_label = QLabel("0 EGP")

        self.total_label.setStyleSheet("""
        font-size: 24px;
        color: #00ffcc;
        """)

        left_layout.addWidget(self.total_label)

        # ================== BUTTONS ==================
        self.add_btn = QPushButton("Add Product")
        self.inventory_btn = QPushButton("Inventory")
        self.dashboard_btn = QPushButton("dashboard")
        self.reports_btn = QPushButton("Reports")
        self.complete_btn = QPushButton("Complete Sale")
        self.history_btn = QPushButton("Sales History")

        if self.role == "cashier":

            self.add_btn.hide()
            self.inventory_btn.hide()
            self.dashboard_btn.hide()
            self.reports_btn.hide()

        elif self.role == "inventory":

            self.dashboard_btn.hide()
            self.reports_btn.hide()

        elif self.role == "accountant":

            self.add_btn.hide()
            self.inventory_btn.hide()

        for btn, func in [

            (self.add_btn, self.open_add_product),
            (self.inventory_btn, self.open_inventory),
            (self.dashboard_btn, self.open_dashboard),
            (self.reports_btn, self.open_reports),
            (self.complete_btn, self.handle_complete_sale),
            (self.history_btn, self.open_history),
        ]:

            btn.clicked.connect(func)

            right_layout.addWidget(btn)

        main_layout.addLayout(left_layout, 3)
        main_layout.addLayout(right_layout, 1)

        self.setLayout(main_layout)

    # ================== OPEN WINDOWS ==================
    def open_add_product(self):
        AddProductDialog().exec()

    def open_inventory(self):
        InventoryDialog().exec()

    def open_dashboard(self):
        DashboardDialog().exec()

    def open_reports(self):
        ReportsDialog().exec()

    def open_history(self):
        SalesHistoryDialog().exec()

    # ================== ADD PRODUCT ==================
    def add_product(self):

        barcode = self.barcode_input.text()

        product = SalesService.get_product_by_barcode(barcode)

        if not product:

            winsound.Beep(300, 700)

            self.barcode_input.clear()

            return

        name, price, stock = product

        if stock <= 0:

            winsound.Beep(300, 700)

            print("❌ Out Of Stock")

            return

        for item in self.cart:

            if item["barcode"] == barcode:

                item["qty"] += 1

                self.update_table()

                winsound.Beep(1000, 200)

                self.barcode_input.clear()

                return

        self.cart.append({
            "barcode": barcode,
            "name": name,
            "price": price,
            "qty": 1
        })

        winsound.Beep(1000, 200)

        self.update_table()

        self.barcode_input.clear()

    # ================== UPDATE TABLE ==================
    def update_table(self):

        self.table.setRowCount(0)

        total = 0

        for row_idx, item in enumerate(self.cart):

            self.table.insertRow(row_idx)

            item_total = item["qty"] * item["price"]

            total += item_total

            self.table.setItem(
                row_idx,
                0,
                QTableWidgetItem(item["name"])
            )

            self.table.setItem(
                row_idx,
                1,
                QTableWidgetItem(str(item["qty"]))
            )

            self.table.setItem(
                row_idx,
                2,
                QTableWidgetItem(str(item["price"]))
            )

            self.table.setItem(
                row_idx,
                3,
                QTableWidgetItem(str(item_total))
            )

            btn = QPushButton("✖")

            btn.clicked.connect(
                lambda checked, i=row_idx: self.remove_item(i)
            )

            self.table.setCellWidget(row_idx, 4, btn)

        self.total_label.setText(f"{total} EGP")

    # ================== REMOVE ITEM ==================
    def remove_item(self, index):

        if index < len(self.cart):

            del self.cart[index]

            self.update_table()

            winsound.Beep(400, 100)

    # ================== COMPLETE SALE ==================
    def handle_complete_sale(self):

        if not self.cart:
            return

        total = SalesService.complete_sale(
            self.cart,
            self.username
        )

        print_receipt(
            self.cart,
            total,
            self.username
        )


        self.cart = []

        self.update_table()

        winsound.Beep(1500, 300)
class SalesHistoryDialog(QDialog):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Sales History")
        self.resize(900, 500)

        layout = QVBoxLayout()

        self.table = QTableWidget()

        self.table.setColumnCount(5)

        self.table.setHorizontalHeaderLabels([
            "ID",
            "Date",
            "Total",
            "Cashier",
            "Refund"
        ])

        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )

        layout.addWidget(self.table)

        self.setLayout(layout)

        self.load_sales()

    def load_sales(self):

        conn = sqlite3.connect("database/store.db")
        cursor = conn.cursor()

        cursor.execute("""
        SELECT id, date, total_price, cashier_name
        FROM sales
        ORDER BY id DESC
        """)

        sales = cursor.fetchall()

        self.table.setRowCount(0)

        for row_idx, sale in enumerate(sales):

            self.table.insertRow(row_idx)

            for col_idx, value in enumerate(sale):

                self.table.setItem(
                    row_idx,
                    col_idx,
                    QTableWidgetItem(str(value))
                )

            refund_btn = QPushButton("Refund")

            refund_btn.setStyleSheet("""
            background-color:red;
            color:white;
            """)

            refund_btn.clicked.connect(
                partial(self.open_refund_dialog, sale[0])
            )

            self.table.setCellWidget(
                row_idx,
                4,
                refund_btn
            )

        conn.close()

    def open_refund_dialog(self, sale_id):

        dialog = RefundDialog(sale_id)

        dialog.exec()

        self.load_sales()


# ================== REFUND ITEMS ==================
class RefundDialog(QDialog):
    def __init__(self, sale_id):
        super().__init__()

        self.sale_id = sale_id

        self.setWindowTitle("Refund Items")
        self.resize(700, 400)

        layout = QVBoxLayout()

        self.table = QTableWidget()

        self.table.setColumnCount(5)

        self.table.setHorizontalHeaderLabels([
            "Product",
            "Bought Qty",
            "Refund Qty",
            "Price",
            "Refund"
        ])

        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )

        layout.addWidget(self.table)

        self.setLayout(layout)

        self.load_items()

    def load_items(self):

        conn = sqlite3.connect("database/store.db")
        cursor = conn.cursor()

        cursor.execute("""
        SELECT id, product_name, quantity, total_price
        FROM sales_items
        WHERE sale_id=?
        """, (self.sale_id,))

        items = cursor.fetchall()

        self.table.setRowCount(0)

        for row_idx, item in enumerate(items):

            item_id, product_name, qty, total_price = item

            self.table.insertRow(row_idx)

            price_per_item = total_price / qty

            self.table.setItem(
                row_idx,
                0,
                QTableWidgetItem(product_name)
            )

            self.table.setItem(
                row_idx,
                1,
                QTableWidgetItem(str(qty))
            )

            spin = QSpinBox()
            spin.setMinimum(1)
            spin.setMaximum(qty)

            self.table.setCellWidget(
                row_idx,
                2,
                spin
            )

            self.table.setItem(
                row_idx,
                3,
                QTableWidgetItem(str(price_per_item))
            )

            refund_btn = QPushButton("Refund")

            refund_btn.setStyleSheet("""
            background-color:red;
            color:white;
            """)

            refund_btn.clicked.connect(
                partial(
                    self.refund_item,
                    item_id,
                    product_name,
                    qty,
                    price_per_item,
                    spin
                )
            )

            self.table.setCellWidget(
                row_idx,
                4,
                refund_btn
            )

        conn.close()

    def refund_item(
            self,
            item_id,
            product_name,
            old_qty,
            price_per_item,
            spin
    ):

        refund_qty = spin.value()

        conn = sqlite3.connect("database/store.db")
        cursor = conn.cursor()

        # رجع للمخزن
        cursor.execute("""
        UPDATE products
        SET quantity = quantity + ?
        WHERE name=?
        """, (
            refund_qty,
            product_name
        ))

        new_qty = old_qty - refund_qty

        new_total = new_qty * price_per_item

        # لو المنتج خلص من الفاتورة
        if new_qty <= 0:

            cursor.execute("""
            DELETE FROM sales_items
            WHERE id=?
            """, (item_id,))

        else:

            cursor.execute("""
            UPDATE sales_items
            SET quantity=?, total_price=?
            WHERE id=?
            """, (
                new_qty,
                new_total,
                item_id
            ))

        # تحديث إجمالي الفاتورة
        cursor.execute("""
        SELECT SUM(total_price)
        FROM sales_items
        WHERE sale_id=?
        """, (self.sale_id,))

        new_sale_total = cursor.fetchone()[0]

        # لو الفاتورة فضيت
        if new_sale_total is None:

            cursor.execute("""
            DELETE FROM sales
            WHERE id=?
            """, (self.sale_id,))

        else:

            cursor.execute("""
            UPDATE sales
            SET total_price=?
            WHERE id=?
            """, (
                new_sale_total,
                self.sale_id
            ))

        conn.commit()
        conn.close()

        self.load_items()

        print("✅ Partial Refund Done")

# ================== RUN ==================
if __name__ == "__main__":

    from auth import init_users

    init_users()

    app = QApplication(sys.argv)

    login = LoginWindow()

    if login.exec():
        window = CashierApp(
            login.role,
            login.username_value
        )

        window.show()

        sys.exit(app.exec())