import streamlit as st
import numpy as np
import os
import cv2
import pickle
from tf_keras.models import load_model
from helpers import resize_to_fit
import imutils
from PIL import Image
import webbrowser
import time

# Load the model and labels
MODEL_FILENAME = "captcha_model.hdf5"
MODEL_LABELS_FILENAME = "model_labels.dat"

with open(MODEL_LABELS_FILENAME, "rb") as f:
    lb = pickle.load(f)

model = load_model(MODEL_FILENAME)

def preprocess_and_predict(image):
    """Process the image and predict the CAPTCHA text."""
    image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    image = cv2.copyMakeBorder(image, 20, 20, 20, 20, cv2.BORDER_REPLICATE)
    thresh = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
    contours = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = contours[1] if imutils.is_cv3() else contours[0]

    letter_image_regions = []

    for contour in contours:
        (x, y, w, h) = cv2.boundingRect(contour)

        if w / h > 1.25:
            half_width = int(w / 2)
            letter_image_regions.append((x, y, half_width, h))
            letter_image_regions.append((x + half_width, y, half_width, h))
        else:
            letter_image_regions.append((x, y, w, h))

    if len(letter_image_regions) != 4:
        return None, "Incorrect number of letters detected."

    letter_image_regions = sorted(letter_image_regions, key=lambda x: x[0])
    output = cv2.merge([image] * 3)
    predictions = []

    for letter_bounding_box in letter_image_regions:
        x, y, w, h = letter_bounding_box
        letter_image = image[y - 2:y + h + 2, x - 2:x + w + 2]
        letter_image = resize_to_fit(letter_image, 20, 20)
        letter_image = np.expand_dims(letter_image, axis=2)
        letter_image = np.expand_dims(letter_image, axis=0)

        prediction = model.predict(letter_image)
        letter = lb.inverse_transform(prediction)[0]
        predictions.append(letter)

        cv2.rectangle(output, (x - 2, y - 2), (x + w + 4, y + h + 4), (0, 255, 0), 1)
        cv2.putText(output, letter, (x - 5, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2)

    captcha_text = "".join(predictions)
    return output, captcha_text

# Streamlit app layout
st.title("CAPTCHA Solver")

uploaded_file = st.file_uploader("Upload CAPTCHA Image", type=["png", "jpg", "jpeg", "bmp"])

if uploaded_file is not None:
    # Read the image file
    image = Image.open(uploaded_file)
    image = np.array(image)

    # Process the image and get predictions
    output_image, captcha_text = preprocess_and_predict(image)

    if output_image is None:
        st.error(captcha_text)
    else:
        # Display the results
        st.image(output_image, channels="RGB", caption="Annotated CAPTCHA", use_column_width=True)
        st.success(f"Predicted CAPTCHA text: {captcha_text}")
