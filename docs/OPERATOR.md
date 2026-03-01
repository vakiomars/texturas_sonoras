# Operador canónico (MGI activo)

Este documento define el **núcleo matemático** del Motor Generativo Iterativo (MGI) y su mapeo directo a código.

## 1) Estado, espacio y trayectoria

- Espacio de estados: \(X \subseteq \mathbb{R}^n\)
- Estado: \(x_k \in X\)
- Condición inicial: \(x_0\) (duración finita; *semilla estructural*)

El motor genera una trayectoria \(\{x_k\}_{k\ge 0}\).

## 2) Transformador generativo

\[
z_{k+1} = T(x_k; \theta, s_k)
\]

- \(T\): transformador (en audio: DSP/granular; en otros dominios: transformador de series, campos discretos, etc.)
- \(s_k\): semilla/política de reproducibilidad

## 3) Embedding del ancla

Si \(z_{k+1}\) no tiene la misma dimensión que \(x_0\), se define un embedding determinista:

\[
\hat{x}_0 = E(x_0; \mathrm{len}(z_{k+1}))
\]

En audio esto suele ser “tile + crossfade” para evitar costuras.

## 4) Mezcla anclada

\[
\tilde{x}_{k+1}(\alpha) = (1-\alpha)\,\hat{x}_0 + \alpha\,z_{k+1}
\]

\(\alpha\in[0,1]\) controla preservación vs difusión.

## 5) Descriptor estructural y distancia

Se define un descriptor universal mínimo por momentos:

\[
\Phi(x)=\begin{bmatrix}
\mu(x)\\
\sigma^2(x)\\
\kappa(x)\\
H(x)
\end{bmatrix}
\]

Y una distancia:

\[
d(x,y)=\|W(\Phi(x)-\Phi(y))\|_2
\]

Esto permite medir:

- Preservación global: \(d(x_k,x_0)\)
- Estabilidad incremental: \(d(x_{k+1},x_k)\)

## 6) Conjunto válido \(C\) y proyección \(\Pi_C\)

\(C\) se define como el conjunto de estados que respetan invariantes (tolerancias) respecto a \(x_0\).

Ejemplo mínimo (momentos):

\[
C_{\text{mom}} = \{x: |\Phi_i(x)-\Phi_i(x_0)|\le \delta_i\}\,.
\]

En audio (sandbox) se añade:

- Energía (RMS) en tolerancia
- Headroom (sample-peak) como proxy conservador de true-peak

La proyección \(\Pi_C\) devuelve el estado a \(C\) de forma determinista (match de media/RMS y headroom; hist-match opcional).

## 7) Control activo (backtracking sobre \(\alpha\))

Antes de proyectar, el motor evalúa si el candidato \(\tilde{x}_{k+1}(\alpha)\) viola \(C\). Si viola, reduce \(\alpha\) y reintenta:

\[
\alpha \leftarrow \max(\alpha_{\min},\;\beta\alpha),\quad \beta\in(0,1)
\]

Esto evita que el sistema “explote” y reduce correcciones agresivas en \(\Pi_C\).

## 8) Mapeo a código

- `src/mgi/metrics.py`: \(\Phi\), \(d\), RMS/peak/crest
- `src/mgi/constraints.py`: definición de \(C\), `violation()` y `project()` (\(\Pi_C\))
- `src/mgi/operator.py`: `evolve_active()` (backtracking + proyección)
- `src/dsp.py`: transformador de audio (implementa \(T\)) + wrapper `evolve_texture()`
