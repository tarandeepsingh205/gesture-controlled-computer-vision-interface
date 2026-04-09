# gesture-controlled-computer-vision-interface
Real-time gesture-controlled human-computer interface using MediaPipe and OpenCV for touchless interaction.
# Gesture Controlled Computer Interface

A real-time gesture-based human-computer interaction system using computer vision for touchless control.

---

## Features
- 🖱️ Cursor control using index finger
- 🤏 Drag & drop using pinch gesture
- ✌️ Scroll using two fingers
- 🤟 Copy gesture (3 fingers)
- ✊ Paste gesture (fist)
- 🖐️ Tab switching using hand movement

---

##  System Architecture
Camera → MediaPipe → Hand Landmarks → Gesture Recognition → System Control

---

## Setup

```bash
pip install -r requirements.txt
python src/main.py
