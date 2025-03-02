import streamlit as st
import io
import re
from PyPDF2 import PdfReader  # PDF metni çekmek için
import pandas as pd

def extract_text_from_pdf(file):
    """
    Yüklenen PDF dosyasından metni çıkarır.
    """
    reader = PdfReader(file)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text

def extract_cash_flow_data(text):
    """
    PDF metninden nakit akış verilerini regex ile çıkarır.
    Örnek olarak; A. İŞLETME FAALİYETLERİNDEN NAKİT AKIŞLARI,
    B. YATIRIM FAALİYETLERİNDEN NAKİT AKIŞLARI, 
    C. FİNANSMAN FAALİYETLERİNDEN NAKİT AKIŞLARI ve 
    DÖNEM SONU NAKİT VE NAKİT BENZERLERİ bölümlerini arar.
    """
    data = {}

    # A Bölümü: Örnek düzen, ihtiyaca göre düzenleyebilirsiniz.
    match = re.search(
        r'(A\.?\s*(İŞLETME FAALİYETLERİNDEN|FAALİYETLERDEN DOĞAN)\s*NAKİT\s*AKIŞLARI).*?([\-0-9\.,]+)',
        text, re.IGNORECASE | re.DOTALL
    )
    if match:
        data["A. İŞLETME FAALİYETLERİNDEN NAKİT AKIŞLARI"] = match.group(3)

    # B Bölümü
    match = re.search(
        r'(B\.?\s*YATIRIM FAALİYETLERİNDEN\s*NAKİT\s*AKIŞLARI).*?([\-0-9\.,]+)',
        text, re.IGNORECASE | re.DOTALL
    )
    if match:
        data["B. YATIRIM FAALİYETLERİNDEN NAKİT AKIŞLARI"] = match.group(2)

    # C Bölümü
    match = re.search(
        r'(C\.?\s*FİNANSMAN FAALİYETLERİNDEN\s*NAKİT\s*AKIŞLARI).*?([\-0-9\.,]+)',
        text, re.IGNORECASE | re.DOTALL
    )
    if match:
        data["C. FİNANSMAN FAALİYETLERİNDEN NAKİT AKIŞLARI"] = match.group(2)

    # DÖNEM SONU Bölümü
    match = re.search(
        r'(DÖNEM SONU NAKİT VE NAKİT BENZERLERİ).*?([\-0-9\.,]+)',
        text, re.IGNORECASE | re.DOTALL
    )
    if match:
        data["DÖNEM SONU NAKİT VE NAKİT BENZERLERİ"] = match.group(2)

    return data

# Streamlit arayüzü
st.title("PDF Nakit Akış Analizi")

uploaded_file = st.file_uploader("Lütfen analiz için bir PDF dosyası yükleyin", type=["pdf"])

if uploaded_file is not None:
    st.info("PDF dosyası yükleniyor, lütfen bekleyin...")
    # PDF dosyasından metni çıkar
    pdf_text = extract_text_from_pdf(uploaded_file)
    st.subheader("PDF Metni (Önizleme)")
    st.text_area("PDF İçeriği", pdf_text, height=200)

    # PDF metninden nakit akış verilerini çıkar
    cash_flow_data = extract_cash_flow_data(pdf_text)
    if cash_flow_data:
        st.subheader("Nakit Akış Verileri")
        df = pd.DataFrame(list(cash_flow_data.items()), columns=["Bölüm", "Değer"])
        st.dataframe(df)
    else:
        st.error("PDF'den nakit akış verisi çıkarılamadı!")
