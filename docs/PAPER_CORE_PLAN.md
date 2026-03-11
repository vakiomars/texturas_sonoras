# Paper-Faithful Core Plan

## Propósito de esta rama
Esta rama existe para implementar el IGE canónico del paper v5 de forma fiel, separada del adapter de producto audio.

## Estado actual
El repositorio tiene un producto de audio funcional y estable en `main`, pero el gap entre paper e implementación sigue abierto.

### Hito estable de producto
- Tag estable: `hito-nivel1-audio-stable`
- Commit base estable: `ca632e1`

## Gap actual entre paper y código
### En el paper
- Descriptor estructural: STFT power + ACF
- Potencial: J(x) = ||phi(x) - phi(x0)||^2
- Corrector: Pi = G^K con G(x) = x - eta * grad J(x)
- Proposal canónica: T(x,s) = W x + s
- Dos modos: IGE-A e IGE-M
- Teorema MaxEnt en clase Gaussiana

### En el código actual
- Descriptor heurístico no espectral
- Corrector heurístico / proyectivo
- Proposal DSP granular no lineal
- Pipeline pensado para producto audio
- Sin implementación canónica del operador del paper

## Objetivo de nivel 2
Construir una implementación paper-faithful mínima, medible y testeable.

## Alcance mínimo de la primera implementación canónica
1. `phi_spectral(x)`
   - band power STFT
   - autocorrelation lags

2. `J(x, x0)`
   - distancia entre descriptores canónicos

3. `corrector_gd(x, x0, eta, K)`
   - K pasos de gradient descent sobre J

4. `proposal_ou(x, a, sigma, seed)`
   - versión mínima con W = aI

5. modos explícitos
   - `evolve_ige_a(...)`
   - `evolve_ige_m(...)`

6. tests mínimos
   - J disminuye bajo el corrector
   - phi(x_k) se acerca a phi(x0)
   - caso gaussiano simple reproducible

## Regla de congelación
Esta rama se abre hoy, se documenta hoy y NO se desarrolla durante la semana de lanzamiento del producto.

## Condición de descongelamiento
La rama se reabre solo después de:
- producto publicado
- demo pública operativa
- primera ronda de feedback externo

## Regla estratégica
No mezclar producto release con implementación canónica.
Producto y core formal avanzan por ramas separadas.
