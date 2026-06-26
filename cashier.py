import sys
import os
import qrcode
import sqlite3
from datetime import datetime
from reportlab.lib.enums import TA_CENTER

# ================== PDF ==================
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# ================== Arabic Support ==================
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import arabic_reshaper
from bidi.algorithm import get_display

# 🔥 تسجيل الخط العربي (لازم يكون الملف موجود)
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

font_path = resource_path("assets/fonts/Amiri-Regular.ttf")

pdfmetrics.registerFont(
    TTFont('Arabic', font_path)
)

# ================== Arabic Helper ==================
def ar(text):
    reshaped = arabic_reshaper.reshape(str(text))
    return get_display(reshaped)
def ar_safe(text):
    # لو عربي → يعالجه، لو إنجليزي → يسيبه
    if any('\u0600' <= c <= '\u06FF' for c in text):
        return ar(text)
    return text


# ================== GET PRODUCT ==================
def get_product_by_barcode(barcode):
    conn = sqlite3.connect("store.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT name, sell_price, quantity FROM products WHERE barcode=?",
        (barcode,)
    )

    product = cursor.fetchone()
    conn.close()

    return product


# ================== COMPLETE SALE ==================
# ================== COMPLETE SALE ==================
def complete_sale(cart, cashier_name):

    conn = sqlite3.connect("store.db")
    cursor = conn.cursor()

    total = 0

    # احسب الإجمالي الأول
    for item in cart:
        total += item["price"] * item["qty"]

    # سجل الفاتورة الأساسية الأول
    cursor.execute("""
    INSERT INTO sales
    (date, total_price, cashier_name)
    VALUES (?, ?, ?)
    """, (
        datetime.now(),
        total,
        cashier_name
    ))

    sale_id = cursor.lastrowid

    # بعدين سجل المنتجات
    for item in cart:

        barcode = item["barcode"]
        qty = item["qty"]

        cursor.execute("""
        SELECT quantity, sell_price
        FROM products
        WHERE barcode=?
        """, (barcode,))

        product = cursor.fetchone()

        if not product:
            continue

        stock, price = product

        if qty > stock:
            continue

        item_total = price * qty

        # خصم من المخزن
        cursor.execute("""
        UPDATE products
        SET quantity=?
        WHERE barcode=?
        """, (
            stock - qty,
            barcode
        ))

        # تسجيل المنتج في الفاتورة
        cursor.execute("""
        INSERT INTO sales_items
        (product_name, quantity, total_price, date, sale_id)
        VALUES (?, ?, ?, ?, ?)
        """, (
            item["name"],
            qty,
            item_total,
            datetime.now(),
            sale_id
        ))

    conn.commit()
    conn.close()

    return total

# ================== PRINT RECEIPT ==================
def print_receipt(cart, total, cashier_name):
    invoice_id = int(datetime.now().timestamp())
    filename = f"receipt_{invoice_id}.pdf"

    # 🔥 حجم الرول
    page_width = 80 * mm
    base_height = 80
    row_height = 10
    dynamic_height = base_height + (len(cart) * row_height)
    page_height = dynamic_height * mm

    doc = SimpleDocTemplate(
        filename,
        pagesize=(page_width, page_height),
        leftMargin=5,
        rightMargin=5,
        topMargin=5,
        bottomMargin=5
    )

    styles = getSampleStyleSheet()

    # 🔥 ستايل عربي
    arabic_style = ParagraphStyle(
        name='ArabicStyle',
        fontName='Arabic',
        fontSize=10,
        leading=12,
        alignment=TA_CENTER,
    )

    elements = []

    # ================== HEADER ==================

    # ❌ القديم:
    # elements.append(Paragraph("<b>MY STORE</b>", styles['Title']))

    # ✅ الجديد:
    elements.append(Paragraph(ar("البركة ماركت"), arabic_style))
    elements.append(Paragraph(ar("0123456789"), arabic_style))
    elements.append(Spacer(1, 6))

    # ================== INFO ==================

    elements.append(Paragraph(ar(f"فاتورة: {invoice_id}"), arabic_style))
    elements.append(Paragraph(ar(datetime.now().strftime('%Y-%m-%d %H:%M')), arabic_style))
    elements.append(Paragraph(ar(f"الكاشير: {cashier_name}"), arabic_style))
    elements.append(Spacer(1, 6))

    # ================== TABLE ==================

    # ❌ القديم:
    # data = [["Item", "Q", "T"]]

    # ✅ الجديد:
    data = [[ar("المنتج"), ar("الكمية"), ar("السعر")]]

    for item in cart:
        data.append([
            ar_safe(item["name"]),
            str(item["qty"]),
            f"{item['price'] * item['qty']}"
        ])

    data.append(["", ar("الإجمالي"), f"{total}"])

    table = Table(data, colWidths=[35 * mm, 15 * mm, 25 * mm])

    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),

        ("BACKGROUND", (0, 0), (-1, 0), colors.black),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),

        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),

        # 🔥 مهم للعربي
        ("FONTNAME", (0, 0), (-1, -1), "Arabic"),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 8))

    # ================== QR ==================
    qr_data = f"Invoice:{invoice_id} Total:{total}"
    qr = qrcode.make(qr_data)

    qr_path = "temp_qr.png"
    qr.save(qr_path)

    elements.append(Image(qr_path, width=50, height=50))
    elements.append(Spacer(1, 8))

    # ================== FOOTER ==================

    # ❌ القديم:
    # elements.append(Paragraph("Thank you ❤️", styles['Normal']))

    # ✅ الجديد:
    elements.append(Paragraph(ar("شكراً لزيارتكم ❤️"), arabic_style))
    elements.append(Paragraph(ar("نتمنى رؤيتكم مرة أخرى"), arabic_style))

    # BUILD
    doc.build(elements)

    if os.path.exists(qr_path):
        os.remove(qr_path)

    print(f"🧾 Receipt saved: {filename}")
