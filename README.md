<p align="center">
  <img src="https://cdn.discordapp.com/attachments/1403059512130404494/1477647037456584775/IMG_20251224_142130.png?ex=69e37c0b&is=69e22a8b&hm=a0a65fed54895cc90da601bdbd91c19dd4e5814c7d2eda3d0cb9a59a1e7a90c4&" alt="Vortex App Logo" width="600">
</p>

# VORTEX App

### 🚧 Status: Under development
**Version:** 0.0.0 
**Environment:** Windows 10/11 [Version 10.0.26200]

---

## 🌪️ Overview
**VORTEX** is an integrated robotics control and monitoring ecosystem. It bridges the gap between complex hardware operations and user-friendly interfaces, providing real-time telemetry, spatial mapping, and AI-driven voice interactions.

## 🛠️ Project Structure
The application is built with a modular architecture for easy scaling:

* **`main.py`**: The central application entry point.
* **`models/`**: Core logic and UI components.
    * **`panels/`**: UI modules for Servo control, Mapping, Q&A, and Telemetry.
    * **`logic_units/`**: Backend engines including STT (Speech-to-Text) and Authorization.
* **`motion_movment_saved/`**: Storage for recorded robot movement sequences (JSON).
* **`images/`**: Assets for the dynamic UI, including status icons and robot avatars.

## ✨ Core Features
* **Intelligent Control:** Integrated Speech-to-Text (`stt_engine.py`) for voice command processing.
* **Motion Memory:** Record and save robot movements to `.json` files and replay them with high precision.
* **Data-Driven:** Multi-database support (`sqlite3`) for logging, STT history, and dashboard telemetry.
* **Mapping & Navigation:** A dedicated visual panel for environment tracking and spatial data.
* **Secure Access:** Built-in authorization protocols to protect hardware controls.

## 🚀 Installation & Setup

1.  **Clone the Repository:**
    ```bash
    git clone [your-repository-link]
    cd Vortex_App
    ```

2.  **Environment Setup:**
    Run the included batch script to automate the development environment configuration:
    ```cmd
    install_dev_area.bat
    ```

3.  **Run Application:**
    ```cmd
    python main.py
    ```

## 📝 Notes
* **Current OS:** Optimized for Microsoft Windows [Version 10.0.26200.6584].
* **Database:** Uses `lamma_aq.db` and `robot_dashboard.db` for local storage.

---
<p align="center"><i>© 2026 Vortex Robotics Project - Built for the future of automation.</i></p>
