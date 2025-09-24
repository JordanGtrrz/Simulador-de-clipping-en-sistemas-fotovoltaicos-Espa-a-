# Simulador-de-clipping-en-sistemas-fotovoltaicos-Espa-a-
Aplicación interactiva en Streamlit para simular la producción de energía de sistemas fotovoltaicos en cualquier provincia de España, usando datos horarios de irradiancia y temperatura obtenidos en tiempo real desde PVGIS (European Commission).

👉 [Abrir la app en Streamlit Cloud]([https://tuusuario-solar-clipping.streamlit.app](https://clipping-pv-esp.streamlit.app/)) 

Características principales
- Selección de **provincia española** o **coordenadas personalizadas**.
- Descarga automática de series horarias de irradiancia y temperatura desde **PVGIS**.
- Cálculo de **potencia DC** considerando PR, NOCT y coeficiente de temperatura.
- Modelado del **inversor** con eficiencia configurable y ratio **DC/AC** ajustable.
- Visualizaciones dinámicas:
  - Curvas horarias del día pico (DC vs AC vs clipping).
  - Mapa de calor de pérdidas por clipping por mes y ratio DC/AC.
  - Resumen mensual descargable en CSV.
- Enfoque **educativo y divulgativo**: muestra cómo influye el sobredimensionamiento del campo FV frente a la potencia nominal del inversor.

---
Instalación en local
Clona el repositorio y entra en la carpeta del proyecto:


git clone https://github.com/TU_USUARIO/solar-clipping.git
cd solar-clipping
