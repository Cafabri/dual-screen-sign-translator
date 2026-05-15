import sys
import os

ROOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, ROOT_DIR)
os.chdir(ROOT_DIR)

import streamlit as st
from dashboard.loaders import (
    load_history, load_confusion_matrix_data, load_softmax_samples,
    LSTM_HISTORY_PATH, DENSE_HISTORY_PATH,
)
from dashboard.charts import (
    render_accuracy_comparison, render_loss_curves,
    render_confusion_matrix, render_softmax_distribution,
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def chart_block(title: str):
    """Renders a labelled container that visually separates a chart from the prose."""
    st.markdown(f"#### 📊 {title}")


def missing_data_notice(script: str):
    st.info(f"Ejecuta `{script}` para generar los datos de este gráfico.", icon="ℹ️")


# ── Sidebar ────────────────────────────────────────────────────────────────────

def render_sidebar(lstm_history):
    with st.sidebar:
        st.title("DualSign")
        st.caption("Informe interactivo de Fase 3")
        st.divider()

        if lstm_history:
            st.metric("Test Accuracy final", f"{lstm_history['test_accuracy'] * 100:.2f}%")
            st.metric("Épocas ejecutadas", len(lstm_history["loss"]))
            st.metric("Mejor Val Accuracy", f"{max(lstm_history['val_accuracy']) * 100:.2f}%")
        else:
            st.warning("Historial no disponible.")

        st.divider()
        st.markdown("**Índice del informe**")
        st.markdown("""
- [1. Resumen Ejecutivo](#sec-1)
- [2. Preprocesamiento](#sec-2)
- [3. Arquitectura LSTM](#sec-3)
- [4. Estrategia de Entrenamiento](#sec-4)
- [5. Primera Iteración](#sec-5)
- [6. Data Augmentation](#sec-6)
- [6.5 Desbalance de Clases](#sec-6-5)
- [7. Limitaciones ISLR/CSLR](#sec-7)
- [8. Mitigación en Software](#sec-8)
- [9. Conclusiones](#sec-9)
        """)

        st.divider()
        st.markdown("**Dataset**")
        st.markdown("- 88 vídeos originales (WLASL)")
        st.markdown("- ×10 Data Augmentation → **880 muestras** base")
        st.markdown("- +25 extras para `bye` → **905 muestras** total")
        st.markdown("- 10 clases · Split 80/20")
        st.divider()
        st.markdown("**Arquitectura**")
        st.markdown("- LSTM(128) → Dropout(0.5)")
        st.markdown("- LSTM(64) → Dropout(0.5)")
        st.markdown("- Dense(64) → Dropout(0.3)")
        st.markdown("- Dense(10, Softmax)")
        st.divider()
        st.markdown("**Proyecto:** [DualSign TFG](https://github.com)")
        st.caption("Trabajo de Fin de Grado")


# ── Section renderers ──────────────────────────────────────────────────────────

def render_header():
    st.title("Fase 3 — Entrenamiento, Optimización y Diseño de Despliegue del Modelo LSTM")
    st.markdown("""
**Proyecto:** DualSign — Traductor Bidireccional en Tiempo Real de Lenguaje de Señas Americano
**Fase:** Entrenamiento del Modelo de Red Neuronal Secuencial (LSTM)
**Resultado final:** Test Accuracy **82.32%** · Dataset final: **905 muestras** (880 base + 25 extras para `bye`)
    """)
    st.divider()


def render_section_1():
    st.header("1. Resumen Ejecutivo", anchor="sec-1")
    st.markdown("""
El objetivo central de esta fase fue entrenar un modelo de aprendizaje profundo capaz de resolver
un problema de **clasificación multiclase sobre secuencias temporales**: dado un segmento de vídeo
de una persona ejecutando un signo en ASL, representado como una secuencia de fotogramas con datos
biomecánicos de posición corporal, el modelo debe predecir a cuál de las 10 palabras del vocabulario
MVP pertenece ese gesto.

Esta fase atravesó tres iteraciones técnicas diferenciadas. La primera iteración, entrenada sobre
los 88 vídeos originales, produjo un **Test Accuracy del 33.33%** —resultado que, aunque superior
al azar, reveló un diagnóstico inequívoco de **overfitting por escasez de datos**. La segunda
iteración, tras aplicar un pipeline de **Data Augmentation matricial** que expandió el dataset a
880 muestras, alcanzó un **Test Accuracy del 81.25%**, demostrando que la arquitectura era correcta
desde el principio y que el cuello de botella era exclusivamente el volumen de datos. La tercera
iteración abordó el **desbalance de clases residual**: augmentación adicional para `bye` y pesos de
muestra inversamente proporcionales a la frecuencia de clase elevaron el Test Accuracy final al
**82.32%**, al costo de una redistribución de errores en el clúster visual `no`/`yes`/`apple`.

Este documento narra el arco completo de esa investigación: desde el diseño de la arquitectura
hasta el descubrimiento de sus limitaciones en escenarios de uso continuo, y la estrategia de
ingeniería de software diseñada para mitigarlas en la capa de despliegue web.
    """)


def render_section_2():
    st.header("2. Preprocesamiento y Preparación de Datos", anchor="sec-2")
    st.markdown("""
### 2.1 La Anatomía del Tensor de Entrada

El tensor de entrenamiento `X_train` presenta la forma **(N, 30, 1629)**, donde cada dimensión
tiene un significado físico preciso:

- **N (muestras):** El número total de secuencias de entrenamiento, que varía entre iteraciones
  (70 en la primera con datos originales, 704 en la segunda tras la augmentación).
- **30 (pasos de tiempo / frames):** Cada vídeo ha sido normalizado a exactamente 30 fotogramas
  mediante *padding* o truncado. El modelo procesa el gesto fotograma a fotograma, en orden
  cronológico, como si leyera una frase palabra por palabra.
- **1629 (características / landmarks):** Cada fotograma está representado por un vector de 1.629
  valores numéricos procedentes de **MediaPipe Holistic**: 468 puntos del mapa facial, 33 de la
  pose corporal, y 21 por cada mano × 3 coordenadas (x, y, z).

La red neuronal no "ve" un vídeo; procesa una **matriz de números** que codifica la geometría del
cuerpo humano a lo largo del tiempo.

### 2.2 Por qué One-Hot Encoding y no Etiquetas Numéricas

Si la red recibiera el número `5` para `please` y el `9` para `yes`, sus parámetros interpretarían
que existe una relación de magnitud entre las clases —completamente falsa. El **One-Hot Encoding**
elimina este sesgo representando cada clase como un vector binario donde solo el índice correcto
vale `1`:

```
"hello" → [1, 0, 0, 0, 0, 0, 0, 0, 0, 0]
"bye"   → [0, 1, 0, 0, 0, 0, 0, 0, 0, 0]
```

### 2.3 La Inviolabilidad de la División 80% / 20%

Evaluar un modelo con sus propios datos de entrenamiento —**data leakage**— produce métricas
ilusorias: el modelo memoriza en lugar de generalizar. La partición 80/20 con `stratify=Y_raw`
establece la frontera de honestidad epistemológica del experimento. Solo la métrica sobre el
conjunto de test tiene validez científica.
    """)


def render_section_3(lstm_history, dense_history):
    st.header("3. Justificación de la Arquitectura LSTM", anchor="sec-3")
    st.markdown("""
### 3.1 Por qué LSTM y no una Red Densa Clásica

Una red neuronal densa estándar trata los 30 fotogramas del gesto como 30 entradas independientes
y sin orden, **destruyendo la información temporal**. Reconocer un signo de ASL es análogo a
reconocer una palabra hablada: el significado no reside en ningún instante aislado, sino en la
evolución temporal de la posición de los articuladores.

Las **redes LSTM** mantienen un estado oculto mediante tres puertas internas (*forget*, *input*,
*output*). Al procesar el fotograma 15, el modelo ya ha integrado la información de los fotogramas
1 al 14, captando patrones de trayectoria que son la esencia gramatical del lenguaje de signos.

- **LSTM 1 (128 unidades, `return_sequences=True`):** Extrae patrones locales de bajo nivel.
- **LSTM 2 (64 unidades, `return_sequences=False`):** Sintetiza el gesto completo en un único
  vector de contexto de 64 dimensiones.

El gráfico siguiente confirma empíricamente esta ventaja: la LSTM supera consistentemente a una
red densa equivalente entrenada sobre los mismos datos.
    """)

    chart_block("LSTM vs. Red Densa — Accuracy de Validación por Época")
    if lstm_history and dense_history:
        render_accuracy_comparison(lstm_history, dense_history)
    else:
        missing = []
        if not lstm_history:  missing.append("scripts/train_model.py")
        if not dense_history: missing.append("scripts/train_dense_baseline.py")
        missing_data_notice(" y ".join(missing))

    st.markdown("""
### 3.2 El Rol de las Capas Dropout

Las capas **Dropout** apagan aleatoriamente un porcentaje de neuronas en cada iteración de
entrenamiento, impidiendo que la red memorice los ejemplos específicos en lugar de generalizar
los patrones del gesto. Los valores elegidos —0.5 tras las capas LSTM y 0.3 ante la salida—
reflejan la agresividad de regularización necesaria para un dataset pequeño.

El gráfico de curvas de pérdida muestra que train loss y val loss descienden de forma paralela y
convergente: evidencia directa de que el Dropout está cumpliendo su función.
    """)

    chart_block("Efecto del Dropout — Train Loss vs. Val Loss")
    if lstm_history:
        render_loss_curves(lstm_history)
    else:
        missing_data_notice("scripts/train_model.py")

    st.markdown("""
### 3.3 La Capa de Salida: Dense(10) + Softmax

La función de activación **Softmax** transforma el vector de contexto en una distribución de
probabilidad sobre las 10 clases: 10 valores positivos que suman exactamente `1.0`, interpretables
directamente como la confianza del modelo en cada palabra.
    """)


def render_section_4():
    st.header("4. Compilación y Estrategia de Entrenamiento", anchor="sec-4")
    st.markdown("""
### 4.1 Función de Pérdida: Categorical Crossentropy

La **entropía cruzada categórica** mide la distancia entre la distribución predicha y la real
(el vector One-Hot). Penaliza severamente las predicciones erróneas con alta confianza,
creando un gradiente que obliga al modelo a no solo acertar, sino a calibrar correctamente
su certeza.

### 4.2 Optimizador Adam

**Adam** adapta la tasa de aprendizaje individualmente para cada parámetro del modelo combinando
momentum y gradientes adaptativos. Con `learning_rate=0.001` ofrece convergencia estable en la
gran mayoría de arquitecturas de aprendizaje profundo.

### 4.3 Early Stopping

Configurado con `monitor="val_loss"`, `patience=15` y `restore_best_weights=True`. Sin esta
salvaguarda, el entrenamiento continuaría sobreajustando los pesos más allá del punto de mejor
generalización. En la primera iteración se detuvo en la época 64 de un máximo de 100.
    """)


def render_section_5():
    st.header("5. Primera Iteración: Diagnóstico del Overfitting", anchor="sec-5")
    st.markdown("""
### 5.1 Resultado inicial: 33.33% de Test Accuracy

El primer entrenamiento —sobre los 88 vídeos originales, ~7 por clase— produjo un Test Accuracy
del **33.33%**. El punto de referencia es clave: un clasificador aleatorio obtendría un **10%**
(1 entre 10). Nuestro modelo multiplicó por **3.33×** la precisión aleatoria, demostrando que
extraía patrones reales.

Sin embargo, la brecha entre train accuracy y val accuracy señalaba un overfitting claro. El
diagnóstico fue preciso: **el cuello de botella no era la arquitectura ni el código, sino el
volumen de datos**.

### 5.2 El Hambre de Datos de las Redes Profundas

Con ~954.000 parámetros ajustables y apenas 70 ejemplos de entrenamiento, el modelo tenía
demasiados grados de libertad. En lugar de aprender que "hello es una trayectoria de la mano
hacia la frente", aprendía que "hello es exactamente como lo hizo el actor del vídeo 27172".
Esta memorización de rasgos idiosincráticos es la definición de overfitting.
    """)


def render_section_6(cm_data):
    st.header("6. Resolución del Overfitting: Data Augmentation Matricial", anchor="sec-6")
    st.markdown("""
### 6.1 El Principio de la Augmentación sobre Tensores

Cuando los datos reales son escasos, la solución es generar **muestras sintéticas** matemáticamente
distintas pero semánticamente equivalentes: perturbaciones que representen variaciones realistas
del mundo real sin alterar el significado del gesto.

A diferencia de la augmentación clásica de imágenes, aquí operamos directamente sobre
**tensores de landmarks 3D**, lo que exige transformaciones específicas al dominio biomecánico.

### 6.2 Las Tres Transformaciones Implementadas

**Jitter Espacial — Ruido Gaussiano sobre Coordenadas**

```
dato_aumentado = dato_original + ε,   ε ~ N(0, σ)
```
Con σ ∈ [0.003, 0.007]. Simula las micro-variaciones naturales en la ejecución del gesto.

**Scaling Espacial — Escalado Uniforme del Esqueleto**

```
dato_aumentado = dato_original × α,   α ~ U(low, high)
```
Con rangos U(0.88, 0.97) y U(1.03, 1.12). Simula personas más lejos o más cerca de la cámara.

**Time Shift — Desplazamiento Temporal**

```
shifted = roll(sequence, k, axis=0),   k ~ U_discreta(-3, +3)
frames expuestos → 0.0
```
Simula variabilidad en el timing de inicio del signo.

### 6.3 Las 9 Variantes por Muestra Original

| Variante | Transformaciones |
|---|---|
| `aug_jitter_soft` | Jitter σ=0.003 |
| `aug_jitter_hard` | Jitter σ=0.007 |
| `aug_scale_down` | Scale α ∈ [0.88, 0.97] |
| `aug_scale_up` | Scale α ∈ [1.03, 1.12] |
| `aug_shift` | Time shift k ∈ [-3, +3] |
| `aug_jitter_scale` | Jitter + Scale |
| `aug_jitter_shift` | Jitter + Time shift |
| `aug_scale_shift` | Scale + Time shift |
| `aug_full` | Jitter + Scale + Time shift |

### 6.4 Resultado de la Segunda Iteración: Salto al 81.25% de Test Accuracy

El dataset pasó de **88 a 880 muestras** (×10), con ~70 ejemplos por clase en lugar de ~7.
El resultado fue un salto de **33.33% → 81.25%**, validando tres conclusiones:

1. **La arquitectura era correcta desde el inicio.** El mismo modelo, sin ningún cambio
   estructural, pasó de rendimiento mediocre a robusto.
2. **Las transformaciones son semánticamente válidas.** El modelo generaliza sobre el conjunto
   de test —que contiene únicamente muestras originales sin aumentar.
3. **La Data Augmentation sobre landmarks es de alto retorno.** Cero coste de recolección
   adicional; ×10 el dataset; ×2.4 la precisión.

La matriz de confusión siguiente muestra exactamente qué palabras el modelo ya domina y cuáles
todavía presenta cierta ambigüedad:
    """)

    chart_block("Matriz de Confusión — Resultados por Clase tras Data Augmentation")
    if cm_data is not None:
        render_confusion_matrix(cm_data["cm"], cm_data["class_names"])
    else:
        missing_data_notice("scripts/train_model.py")

    st.markdown("""
### Cómo leer esta matriz

Cada fila es una clase real; cada columna, una clase predicha. La **diagonal principal** son los aciertos:
valores altos en diagonal y ceros fuera de ella es el objetivo. Cualquier celda fuera de la diagonal
es un error: indica que el modelo confundió la fila con la columna.

### Por qué las 6 clases perfectas no cometen ningún error

`bye`, `hello`, `help`, `more`, `please` y `thank_you` alcanzan el **100%** porque sus trayectorias de
landmarks no se solapan con ninguna otra clase. `help` y `more` tienen configuraciones de mano únicas
(extensión de pulgar, puño desplazado) que no aparecen en ninguna otra palabra. `hello` y `thank_you`
incluyen movimiento desde o hacia la cabeza —región que `no`, `yes`, `apple` o `water` no alcanzan.
El modelo construye fronteras de decisión tan amplias que la clase ganadora no cambia incluso con ruido.

### Por qué falla el clúster `apple` / `no` / `water` / `yes`

Estos cuatro signos comparten un rasgo geométrico: la mano se mueve en un espacio **acotado a nivel de
pecho, muñeca o barbilla**, sin los movimientos expansivos que caracterizan al resto del vocabulario.
En el espacio de 1.629 dimensiones de landmarks, sus trayectorias forman un clúster de alta similitud.

- **`apple` (68.2%, 15/22):** El giro de muñeca junto a la mejilla genera landmarks similares al cierre
  de dos dedos de `no`. 6 de 22 muestras se clasifican como `no`.
- **`no` (63.6%, 14/22):** La confusión con `yes` (6 errores) es la más frecuente. Ambos son movimientos
  pequeños a nivel de pecho con coordenadas globales casi idénticas en el espacio de MediaPipe.
- **`water` (66.7%, 12/18):** Los tres dedos en la barbilla activan landmarks en la zona facial/cuello
  que se solapan con los de `bye`. 5 de 18 muestras se clasifican como `bye`.
- **`yes` (54.2%, 13/24):** La clase más débil: se confunde con cuatro clases distintas (`thank_you` ×4,
  `bye` ×3, `water` ×2, `no` ×2). El puño que asiente no ocupa una región bien delimitada porque el
  dataset tiene pocas muestras originales diversas de este signo.

La causa no es la arquitectura: es la escasez de vídeos reales en estas 4 palabras. La augmentación
sintética ya extrajo todo el valor posible de los vídeos existentes.
    """)

    st.subheader("6.5 Tercera Iteración: Corrección del Desbalance de Clases y sus Efectos", anchor="sec-6-5")
    st.markdown("""
### El Problema: Escasez Desigual por Clase

El dataset original no era uniformemente escaso: mientras clases como `help` contaban con hasta
14 vídeos originales, `bye` disponía de únicamente **5 vídeos**. Con la augmentación estándar ×10,
`bye` acumuló 50 muestras frente a las ~140 de `help`. El resultado era predecible: el modelo
alcanzaba apenas un **20% de accuracy en `bye`** —1 de cada 5 muestras de test correctas— lo que
la convertía en una clase prácticamente inútil en producción. `water` registraba un 50%, igualmente
insuficiente.

### Intervención 1: Augmentación Extra para `bye`

Se añadieron 5 variantes adicionales por cada uno de los 5 vídeos originales de `bye`, con
parámetros más agresivos que los de la augmentación base:

| Variante extra | Transformación |
|---|---|
| `aug_jitter_v2` | Jitter σ=0.012 (vs. σ=0.007 anterior) |
| `aug_scale_v2` | Scale α ∈ [0.80, 1.20] (rango más amplio) |
| `aug_shift_v2` | Time shift máximo 5 frames (vs. 3) |
| `aug_jitter_scale_v2` | Jitter σ=0.008 + Scale α ∈ [0.85, 1.15] |
| `aug_full_v2` | Jitter + Scale + Shift con parámetros máximos |

`bye` pasó de **50 a 75 muestras** (×15 en lugar de ×10). Dataset total: **905 muestras**.

### Intervención 2: Pesos de Muestra por Clase

La función `compute_sample_weights()` asigna a cada muestra un peso inversamente proporcional a
la frecuencia de su clase:

```
peso_clase_i = N_total / (N_clases × N_muestras_clase_i)
```

Un error en `bye` penaliza el gradiente más que un error equivalente en `help`. El parámetro
`sample_weight` se pasa a `model.fit()` sin alterar la arquitectura ni los datos de test.

### Resultados y Redistribución de Errores

| Clase | Accuracy anterior | Accuracy nueva | Δ |
|---|---|---|---|
| `hello` | 88.9% | 100% | +11.1 pp |
| `thank_you` | 93.3% | 100% | +6.7 pp |
| `bye` | **20.0%** | **100.0%** | **+80 pp** |
| `water` | 50.0% | 66.7% | +16.7 pp |
| `apple` | 81.8% | 68.2% | −13.6 pp |
| `no` | 95.5% | 63.6% | −31.9 pp |
| `yes` | 61.5% | 54.2% | −7.3 pp |

**¿Por qué empeoró el clúster `no`/`yes`/`apple`?** En el espacio de landmarks, `bye`, `no`,
`yes`, `water` y `apple` forman un clúster de similitud geométrica (movimientos acotados, a nivel
de pecho o mano extendida). Al reajustar las fronteras de decisión para que `bye` sea reconocida,
el modelo las desplazó en regiones que afectaron a las clases vecinas del mismo subespacio.
La matriz de confusión lo confirma: `no` colisiona 6 veces con `yes`, y `apple` 6 veces con `no`.
Este fenómeno se denomina **redistribución de errores** y es la consecuencia estructural de
corregir el desequilibrio en un clúster de alta similitud visual.

**Veredicto neto:** accuracy global **81.25% → 82.32%** (pérdida 0.5046 → 0.4691). Más relevante
que el número es el cambio cualitativo: `bye` era completamente inútil; ahora funciona al 100%.
El modelo es **más robusto en producción**: ninguna palabra del vocabulario MVP queda indetectable.
    """)


def render_section_7():
    st.header("7. Limitaciones del Modelo: El Reto del Mundo Real (ISLR vs. CSLR)", anchor="sec-7")
    st.markdown("""
### 7.1 La Distinción Fundamental: Reconocimiento Aislado vs. Continuo

- **ISLR — Isolated Sign Language Recognition:** El sistema recibe una secuencia de frames que
  contiene exactamente un signo, ejecutado desde y hasta una posición neutral. Es el paradigma
  que implementa nuestro modelo.
- **CSLR — Continuous Sign Language Recognition:** El sistema recibe un flujo continuo de vídeo
  con múltiples signos encadenados y debe segmentarlos, reconocerlos y transcribirlos como frase.
  Es el paradigma que describe la comunicación ASL natural.

### 7.2 El Problema Técnico: Contaminación de la Ventana de 30 Frames

Si un usuario encadena signos rápidamente, la red recibe una mezcla de los frames finales del
primer signo y los iniciales del segundo —**ruido estructurado** que no corresponde a ninguna
clase aprendida. El modelo producirá predicciones de baja confianza o, peor, erróneas con
confianza alta.

### 7.3 Por qué Descartar un Modelo CSLR Puro

**Arquitecturas CTC:** Requieren miles de horas de vídeo con anotaciones temporales a nivel de
signo y frase. Ese corpus no existe de forma accesible y gratuita para ASL.

**APIs Comerciales:** No existe ninguna API comercial de reconocimiento de signos con la
cobertura, latencia y condiciones de licencia compatibles con un proyecto académico de código
abierto.

El **CSLR de producción es un problema de investigación activa**, no un componente disponible
para integración directa.
    """)


def render_section_8(softmax_data):
    st.header("8. Mitigación mediante Arquitectura de Software en el Frontend", anchor="sec-8")
    st.markdown("""
### 8.1 El Principio: Resolver en Software lo que no se puede Resolver en el Modelo

La limitación identificada no requiere reentrenar el modelo. Requiere diseñar inteligentemente
la capa de JavaScript que controla cuándo y con qué datos se lanza la inferencia. Se diseñaron
tres mecanismos complementarios.

### 8.2 Sliding Window — Buffer Rodante de 30 Frames

En el navegador del usuario (`/host`), se mantiene una **cola circular de 30 frames** actualizada
en tiempo real. Cada nuevo frame de cámara reemplaza al más antiguo, manteniendo siempre una
ventana deslizante de los 30 frames más recientes. La inferencia siempre opera sobre datos
actualizados y temporalmente contiguos.

### 8.3 Umbral de Confianza — Thresholding sobre Softmax

```
predicción_aceptada = argmax(softmax)   IF   max(softmax) > 0.90
```

Cuando la ventana contiene la transición entre dos signos, las activaciones se distribuyen de
forma difusa —ninguna clase domina con claridad. El umbral del 90% actúa como filtro que rechaza
automáticamente estas transiciones ruidosas.

El gráfico interactivo siguiente muestra este efecto en acción: selecciona una palabra y observa
si su predicción supera el umbral (línea roja) o queda por debajo de él.
    """)

    chart_block("Distribución Softmax — Confianza del modelo por clase")
    if softmax_data is not None:
        render_softmax_distribution(softmax_data, softmax_data["class_names"])
    else:
        missing_data_notice("scripts/train_model.py")

    st.markdown("""
### Cómo leer este gráfico

Cada barra representa la probabilidad asignada a una de las 10 clases para una muestra correcta de la
palabra seleccionada. La barra de la clase correcta debería dominar; si otras barras son comparables,
el modelo está dudando. La **línea roja** en 0.90 es el umbral de producción: solo se emite predicción
si la barra ganadora supera esa línea.

### Qué revelan los resultados reales

| Clase | Confianza | ¿Funciona en producción? |
|---|---|---|
| `help` | 99.99% | ✅ Siempre |
| `more` | 99.99% | ✅ Siempre |
| `hello` | 99.4% | ✅ Siempre |
| `please` | 94.7% | ✅ Siempre |
| `apple` | 94.4% | ✅ Siempre |
| `thank_you` | 92.5% | ✅ Siempre |
| `bye` | 86.9% | ⚠️ Raramente pasa |
| `water` | 83.6% | ⚠️ Raramente pasa |
| `yes` | 72.1% | ❌ Casi nunca pasa |
| `no` | **37.7%** | ❌ **Nunca pasa** |

Las 6 clases con geometría distintiva concentran casi toda la probabilidad en la respuesta correcta.
Las 4 del clúster problemático distribuyen su probabilidad entre varias clases —reflejo directo de la
ambigüedad geométrica en el espacio de landmarks.

El caso extremo es **`no`**: incluso cuando acierta, la confianza queda repartida entre `bye` (31.3%),
`water` (20.9%) y `apple` (18.5%). En producción, `no` **nunca superará el umbral del 90%** y será
completamente silenciada. `yes` y `water` tampoco emitirán con regularidad.

**Implicación:** con el umbral del 90%, solo 6 de 10 palabras funcionan en tiempo real. Para las otras 4
el sistema no produce ninguna salida. Reducir el umbral al **75–80%** permitiría a `water` y `yes`
comenzar a emitir, a costa de más falsos positivos en transiciones entre signos.
    """)

    st.markdown("""
### 8.4 Cooldown Temporal — Bloqueo Post-Detección

Tras cada predicción aceptada, el sistema activa un **bloqueo de 1 segundo** que evita detectar
el mismo signo múltiples veces y otorga al usuario tiempo para volver a la posición neutral.

### 8.5 El Sistema Combinado

```
[Frame nuevo]
    ↓
[Sliding Window actualiza el buffer de 30 frames]
    ↓
[¿Está activo el cooldown?] → SÍ → No inferir
    ↓ NO
[Lanzar inferencia sobre el buffer actual]
    ↓
[max(softmax) > 0.90?] → NO → Descartar (transición o posición neutral)
    ↓ SÍ
[Publicar predicción + Activar cooldown de 1 segundo]
```

Este sistema no es CSLR; es un **ISLR robusto con detección automática de signos limpios**.
    """)


def render_section_9():
    st.header("9. Conclusiones", anchor="sec-9")
    st.markdown("""
Esta fase demostró que el desafío central del reconocimiento de lenguaje de signos en un contexto
académico no es la arquitectura de la red —que resultó ser correcta desde su primera iteración—
sino la ingeniería del dato que la alimenta y del sistema que controla su uso.

Los resultados confirman tres principios que deben guiar las decisiones de la Fase de Despliegue:
    """)
    c1, c2, c3 = st.columns(3)
    c1.success("**El modelo es competente.** 82.32% de Test Accuracy sobre 10 clases. Ninguna clase del vocabulario MVP queda completamente indetectable.")
    c2.warning("**Los límites son conocidos y acotables.** El problema ISLR vs. CSLR es mitigable con diseño de software. La redistribución de errores en `no`/`yes`/`apple` es un límite del dataset actual, no de la arquitectura.")
    c3.info("**La arquitectura de datos es la variable de control dominante.** La próxima mejora de rendimiento requiere más vídeos reales en el clúster `no`/`yes`/`apple`/`bye`/`water`, no ajustar la red.")
    st.divider()
    st.caption("Trabajo de Fin de Grado — DualSign · Versión interactiva de Fase 3")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    st.set_page_config(
        page_title="DualSign — Informe Fase 3",
        page_icon="🤟",
        layout="wide",
    )

    lstm_history  = load_history(LSTM_HISTORY_PATH)
    dense_history = load_history(DENSE_HISTORY_PATH)
    cm_data       = load_confusion_matrix_data()
    softmax_data  = load_softmax_samples()

    render_sidebar(lstm_history)
    render_header()
    render_section_1()
    st.divider()
    render_section_2()
    st.divider()
    render_section_3(lstm_history, dense_history)
    st.divider()
    render_section_4()
    st.divider()
    render_section_5()
    st.divider()
    render_section_6(cm_data)
    st.divider()
    render_section_7()
    st.divider()
    render_section_8(softmax_data)
    st.divider()
    render_section_9()


if __name__ == "__main__":
    main()
