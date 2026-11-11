# TO-DO — Escenas sci-fi y modo fiesta

- [x] Definir la arquitectura de escenas, bancos de ROM, selector, modo fiesta y presupuesto de VRAM/OAM.
- [x] Implementar **Holo Planet**: planeta wireframe, anillos, lunas y órbitas.
- [x] Implementar **Pulse Analyzer**: barras de espectro, waveform, peak hold y pulso BPM.
- [x] Implementar **Vector City**: skyline wireframe en perspectiva con Mode 7/HDMA.
- [x] Implementar **Atomic**: átomo de Bohr, electrones y órbitas animadas.
- [x] Integrar la escena **Lissajous** existente dentro del selector.
- [x] Añadir **selector de escena** con transiciones.
- [x] Añadir **modo fiesta**: auto-ciclo, blackout, brillo, temas de color y HUD mínimo.
- [x] Compilar y probar cada escena en emulador; capturar screenshots.
- [x] Verificar header, checksum y compatibilidad con hardware real.
- [x] Añadir `check_hardware.py`: auditoría estática del `.sfc` (header,
  checksum estándar, vectores, stub de reset, blobs DMA dentro de su banco,
  descriptores de escena, tablas HDMA y listas NMI del Pulse Analyzer).
- [x] Corregir el checksum al algoritmo estándar de SNES (campo de checksum
  como `FF FF 00 00`, es decir, suma del resto + `$01FE`): `$0EEC` /
  complemento `$F113`; Snes9x 1.63 ya informa **Checksum OK**.
- [x] Corregir el orden NMI/forced blank en `StartScene` e `InitTitle`: la NMI
  y el HDMA se desactivan **antes** de forzar blank, para que una NMI de
  vblank no vuelva a encender la pantalla en medio de una subida a VRAM.
- [x] Actualizar el README y generar la ROM final.
- [x] Corregir el arranque en hardware real: espera de dos vblanks antes de
  tocar la PPU, limpieza de los 8 KiB bajos de WRAM, NMI/HDMA desactivados
  primero, `cld`, y checksum estándar recalculado tras el enlace.
- [x] Corregir la fuga de pila al volver al menú con Select (ya no se sale de
  la subrutina con un `jmp`).
- [x] Añadir una sexta escena, **Neon City**, basada en el concepto
  `References/NeonCityConcept.jpg`: sol rayado, skyline, rejilla de neón,
  coche trasero y lluvia/estelas animadas.
- [x] Rehacer **Neon City** para que se parezca de verdad al concepto: rejilla
  del suelo en perspectiva real moviéndose hacia la cámara (M7A/M7B/M7D por
  scanline con HDMA), ciudad más pequeña y densa en el horizonte, sol rayado
  más grande, carretera ancha con líneas magenta y coche rojo como sprites.
- [x] Paleta propia de fondo para Neon City y rampa roja dedicada en la
  paleta de objetos 4 para sombrear el coche.
- [x] Corregir el salto de bucle de **Holo Planet** y **Atomic**: los anillos,
  lunas y órbitas ya completan un número entero de ciclos en los 120 frames.
- [x] Rehacer **Pulse Analyzer** como consola de monitorización **MAGI-01**
  basada en `References/interface1.jpeg`, `interface2.jpeg`, `Interface3.png`
  e `Interface3.html`: fondo **Mode 1** por capas (BG1 estático 4bpp con texto
  5x7 a 6 px, BG2 de barras y agujas 4bpp, BG3 de matriz espectral 2bpp),
  cabecera con franjas de peligro, panel SYNC RATE, ocho barras de espectro con
  peak hold, osciloscopio de 28 puntos, octaedro A.T. FIELD giratorio, panel
  MAGI con MELCHIOR/BALTHASAR/CASPAR, matriz de espectro con scroll vertical y
  pie con reloj y avisos.
- [x] Listas de escrituras VRAM por frame para la consola (solo celdas que
  cambian más un byte de `BG3VOFS`), aplicadas en la NMI; bucle propio de 128
  frames que hace que el scroll de BG3 recorra exactamente 256 px y el salto de
  bucle sea invisible.
- [x] Paleta propia de 64 colores de fondo para Pulse Analyzer (32 para el
  heatmap, 16 para la UI y 16 para las barras) con variantes para los cuatro
  temas; el tema MONO deja la consola como un monitor de fósforo blanco.
- [x] Corregir el indexado de `ThemeBgBanks`/`ThemeObjBanks`, que usaba `tema*2`
  sobre tablas de un byte y hacía que el tema MONO cargase una paleta desde un
  banco inválido (pantalla negra).
- [x] Reorganizar el empaquetado de bancos con *first fit* para que quepan los
  nuevos datos (bancos 2–12) sin partir ningún blob entre dos bancos.
- [x] Rehacer **Holo Planet** como consola NERV en **Mode 1** basada en
  `References/HoloPlanet.png` y `HoloPlanet.html`: cabecera con franjas de
  peligro, paneles de gauges/capas defensa, lecturas flotantes LAT/LON y
  objetivo, espectro de resonancia a todo el ancho y el globo ocupando toda la
  zona derecha.
- [x] Globo holográfico de matriz de puntos: paralelos estáticos en BG2 (no
  cambian al girar en Y), meridianos punteados y partículas en OAM, satélites
  con etiquetas y anillos orbitales.
- [x] **Persistence of vision**: 120 fases de rotación × 2 campos OAM
  complementarios (240 frames) alternados en cada vblank para duplicar los
  sprites visibles del globo.
- [x] Controles del **D-pad**: izquierda/derecha giran el globo a mano y
  arriba/abajo cambian la velocidad de rotación automática (0–4); el thumb del
  gauge de rotación del panel izquierdo sigue la velocidad.
- [x] Escrituras VRAM por fase para las barras de espectro y los beacons (lista
  de pares dirección/entrada aplicada en la NMI) y un pequeño list para el
  thumb del gauge.
- [x] Paleta propia de 16 colores por tema para la consola y el globo, con las
  cuatro variantes (NEON, SOLAR, AURORA, MONO).

## Notas de implementación

- ROM final: 512 KiB LoROM, 16 bancos; código y tablas Lissajous en el banco 0,
  metadatos y recursos compartidos en el banco 1, fondos, frames OAM, tiles
  extra y tablas de Neon City, Pulse Analyzer y Holo Planet en los bancos 2–14.
- Cada escena tiene un descriptor de 16 bytes (fondo Mode 7, tabla de frames
  OAM, escala, scroll, flags y nombre).  Flags: `$01` estela Lissajous en
  tiempo real, `$02` scroll de Vector City, `$04` suelo en perspectiva de
  Neon City, `$08` consola Mode 1 de Pulse Analyzer y `$10` consola Mode 1 de
  Holo Planet.
- Holo Planet, Pulse Analyzer, Vector City y Atomic usan frames OAM
  precalculados de 96 sprites; Holo Planet usa 240 (120 fases de rotación × 2
  campos complementarios que se alternan por *persistence of vision*), Pulse
  Analyzer tiene 128 frames (2.13 s) porque su matriz espectral recorre el
  tilemap de BG3 exactamente una vez por bucle.  Neon City usa uno solo (el
  coche es estático y todo el movimiento lo pone el suelo) y Lissajous conserva
  su estela en tiempo real.
- Holo Planet es Mode 1: BG1 (consola, 4bpp) en `$0000` con mapa en `$3800`,
  BG2 (globo + celdas animadas, 4bpp) en `$2000` con mapa en `$3C00`.  Las
  celdas animadas llevan el bit de prioridad del mapa a 1 para dibujarse sobre
  la consola; el globo estático queda detrás y la consola lo recorta.
- VRAM: fondo Mode 7 desde la palabra 0; Neon City sube el plano completo de
  32 KiB (skyline de 176 texels arriba, celda de rejilla/carretera repetida
  abajo); Pulse Analyzer reutiliza esa zona con BG1 en `$0000`, BG2/BG3 en
  `$3000` y los mapas en `$3400`/`$3800`/`$3C00`; Holo Planet usa BG1 en
  `$0000` (mapa en `$3800`) y BG2 en `$2000` (mapa en `$3C00`).  Tiles de
  sprites desde `$4000` (fuente 4bpp + dots + tiles extra en `$4430`, coche en
  144–201).
- OAM: slots 0–95 para partículas de escena, 96–127 para el HUD.
- Vector City usa HDMA en el canal 4 para una onda suave de `M7VOFS` por
  scanline.
- Neon City usa HDMA en los canales 1–3 (un write de 16 bits por scanline):
  `M7A` escala, `M7B` shear centrado y `M7D` profundidad, de modo que
  `texel_y = y·M7D/256`.  Las 32 tablas de `M7D` se eligen cambiando el puntero
  de origen del HDMA; la banda del plano que muestrea el suelo es periódica, así
  que el salto al final de cada tabla es invisible.
- Pulse Analyzer no usa HDMA: cada frame lleva una lista de pares
  (dirección VRAM, entrada de mapa) para las celdas que cambian y un byte de
  `BG3VOFS`, y la NMI los aplica en vblank (menos de 60 escrituras por frame).
- Temas: NEON, SOLAR, AURORA y MONO, con avance automático en modo fiesta.
  Neon City tiene paleta de fondo propia y la paleta de objetos 4 es una rampa
  roja para el coche.  Pulse Analyzer usa CGRAM 0–63 para su propia paleta de
  64 colores por tema; Holo Planet usa una única paleta de 16 colores
  (CGRAM 0–15) para consola y globo.
- Header verificado: `NEON SCENES`, checksum `$B9F9` / complemento `$4606`,
  SHA-256
  `5fcfc2ae50af00a06697bd28647691702a5dced3a2975ba73e2cd8d0471039ba`.
