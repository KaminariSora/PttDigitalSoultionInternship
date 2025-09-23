def clean_text_file(input_path: str, output_path: str):
    """
    อ่านไฟล์ .txt ที่มี escape เช่น \n, \t แล้วแปลงเป็นข้อความจริง
    จากนั้นบันทึกเป็นไฟล์ใหม่
    """
    with open(input_path, "r", encoding="utf-8") as f:
        raw_text = f.read()

    # แปลงเฉพาะ "\n", "\t", "\r" ที่อยู่ในข้อความ ให้เป็นจริง
    cleaned_text = raw_text.replace("\\n", "\n").replace("\\t", "\t").replace("\\r", "\r")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(cleaned_text)

    print(f"✅ แปลงเสร็จแล้ว -> {output_path}")


# ตัวอย่างการใช้งาน
if __name__ == "__main__":
    clean_text_file("ScrapingData/Data/InputData/combined.txt", "ScrapingData/Data/InputData/combine_output.txt")
