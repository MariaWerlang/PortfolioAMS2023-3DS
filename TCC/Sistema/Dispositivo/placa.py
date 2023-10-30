import cv2
import imutils
import numpy as np
import pytesseract
import mysql.connector
import re
import datetime  # Importe a biblioteca datetime
import time  # Importe a biblioteca time

# Configuração do Tesseract
pytesseract.pytesseract.tesseract_cmd = r'D:\Tesseract\tesseract.exe'

# Inicializa a captura de vídeo da câmera
cap = cv2.VideoCapture(2)

mydb = mysql.connector.connect(
    host="192.168.0.50",
    user="root",
    password="123",
    database="srs_database"
)

a = mydb.cursor()

placa_valida = False

while not placa_valida:
    # Captura um frame da câmera
    ret, frame = cap.read()
    if not ret:
        break  # Sai do loop se não for possível capturar um frame

    # Redimensiona o frame para uma resolução menor para melhor desempenho
    frame = cv2.resize(frame, (600, 400))

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.bilateralFilter(gray, 13, 15, 15)
    edged = cv2.Canny(gray, 30, 200)

    # Encontre os contornos da placa
    contours = cv2.findContours(edged.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    contours = imutils.grab_contours(contours)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:10]
    screenCnt = None

    for c in contours:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.018 * peri, True)

        if len(approx) == 4:
            screenCnt = approx
            break

    if screenCnt is not None:
        cv2.drawContours(frame, [screenCnt], -1, (0, 0, 255), 3)

        # Recorte a região da placa
        mask = np.zeros(gray.shape, np.uint8)
        new_image = cv2.drawContours(mask, [screenCnt], 0, 255, -1)
        new_image = cv2.bitwise_and(frame, frame, mask=mask)

        (x, y) = np.where(mask == 255)
        (topx, topy) = (np.min(x), np.min(y))
        (bottomx, bottomy) = (np.max(x), np.max(y))
        Cropped = gray[topx:bottomx + 1, topy:bottomy + 1]

        # Realize a OCR na região da placa
        text = pytesseract.image_to_string(Cropped, config='--psm 11')

        # Use uma expressão regular para extrair apenas caracteres alfanuméricos
        cleaned_text = re.sub(r'[^a-zA-Z0-9]', '', text)

        print("Detected license plate Number is:", cleaned_text)

        # Consulta SQL com parâmetro
        sql = "SELECT COUNT(id_veiculos) FROM veiculos WHERE placa_veiculo LIKE %s"

        # Tupla de parâmetros
        data = (cleaned_text,)

        # Execute a consulta SQL com os parâmetros
        a.execute(sql, data)

        result = a.fetchone()  # Obtenha o resultado da consulta

        print("Contagem de veículos com a placa 'FBR2A23':", result)

        if result[0] > 0:  # Se a placa for válida (exemplo: contagem maior que 0)
            print("Placa Válida!")
            
            # Consulta SQL com parâmetro
            sql = "SELECT id_veiculos FROM veiculos WHERE placa_veiculo LIKE %s"

            # Tupla de parâmetros
            data = (cleaned_text,)

            # Execute a consulta SQL com os parâmetros
            a.execute(sql, data)

            result_id = a.fetchone()

            # Obtenha a data atual
            data_entrada = datetime.date.today()

            # Obtenha a hora atual
            hora_entrada = datetime.datetime.now().strftime("%H:%M:%S")

            print("Data de entrada:", data_entrada)
            print("Hora de entrada:", hora_entrada)

            # Consulta SQL com parâmetros para inserção de dados
            sql_insert = ("INSERT INTO entrada (id_veiculos, data_entrada, hora_entrada) VALUES (%s, %s, %s)")

            # Desempacote o valor da tupla result_id
            id_veiculo = result_id[0]

            data_insert = (id_veiculo, data_entrada, hora_entrada)

            # Execute a consulta SQL para inserir os dados
            a.execute(sql_insert, data_insert)
            mydb.commit()  # Faça o commit das alterações no banco de dados
        
            # Aguarde 20 segundos antes de continuar
            time.sleep(20)

    # Exibe a imagem com a placa de licença detectada
    cv2.imshow('License Plate Detection', frame)

    # Pressione a tecla 'q' para sair do loop
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Libera os recursos da câmera e fecha as janelas do OpenCV
cap.release()
cv2.destroyAllWindows()
