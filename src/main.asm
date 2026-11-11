; =============================================================================
;  NEON SCENES - a small SNES cartridge demo
;
;  Target: LoROM, 512 KiB, no expansion chips, NTSC (60 Hz).
;  Build:  wla-65816 + wlalink (WLA-DX 10.7)
;
;  Six scenes share a Mode 7 background and a 96-sprite particle layer.
;  Holo Planet, Pulse Analyzer, Vector City, Atomic and Neon City stream
;  precomputed OAM frames from ROM; Lissajous keeps the original real-time
;  comet trail.  A selector, fade transitions and a party mode sit on top.
; =============================================================================

.MEMORYMAP
  SLOTSIZE $8000
  DEFAULTSLOT 0
  SLOT 0 $8000
.ENDME

.ROMBANKSIZE $8000
.ROMBANKS 16

.SNESHEADER
  ID "SNES"
  NAME "NEON SCENES"
  SLOWROM
  LOROM
  CARTRIDGETYPE $00
  ROMSIZE $09
  SRAMSIZE $00
  COUNTRY $01
  LICENSEECODE $00
  VERSION $00
.ENDSNES

.SNESNATIVEVECTOR
  COP   IrqStub
  BRK   IrqStub
  ABORT IrqStub
  NMI   NmiHandler
  IRQ   IrqStub
.ENDNATIVEVECTOR

.SNESEMUVECTOR
  COP   IrqStub
  ABORT IrqStub
  NMI   IrqStub
  RESET Reset
  IRQBRK IrqStub
.ENDEMUVECTOR

; -----------------------------------------------------------------------------
; Direct page variables
; -----------------------------------------------------------------------------
.DEFINE frameCounter   $00   ; 16-bit, incremented by NMI
.DEFINE lastFrame      $02   ; 16-bit, main-loop frame gate
.DEFINE buttons        $04   ; 16-bit auto-joypad state
.DEFINE prevButtons    $06
.DEFINE pressed        $08   ; 16-bit newly pressed
.DEFINE gameMode       $0A
.DEFINE selectedScene  $0B
.DEFINE sceneIndex     $0C
.DEFINE partyMode      $0D
.DEFINE gameParty      $0E
.DEFINE themeIndex     $0F
.DEFINE hudMode        $10
.DEFINE paused         $11
.DEFINE blackout       $12
.DEFINE transitionState $13
.DEFINE pendingScene   $14
.DEFINE brightness     $15
.DEFINE masterBrightness $16
.DEFINE partyTimer     $17   ; 16-bit
.DEFINE hudDirty       $19
.DEFINE frameIndex     $1A   ; 16-bit
.DEFINE frameDmaRequest $1C
.DEFINE frameSrc       $1D   ; 3 bytes
.DEFINE sceneFlags     $20
.DEFINE sceneFrameCount $21
.DEFINE m7ScrollX      $22   ; 16-bit
.DEFINE m7ScrollY      $24   ; 16-bit
.DEFINE scrollAccum    $26   ; 16-bit
.DEFINE scrollRate     $28
.DEFINE sceneScale     $29   ; 16-bit
.DEFINE bgPtr          $2B   ; 3 bytes
.DEFINE bgSize         $2E   ; 16-bit
.DEFINE frameTablePtr  $30   ; 3 bytes
.DEFINE dmaSrc         $33   ; 16-bit
.DEFINE dmaBank        $35
.DEFINE dmaSize        $36   ; 16-bit
.DEFINE oamPtr         $38   ; 16-bit
.DEFINE oamX           $3A
.DEFINE oamY           $3B
.DEFINE oamAttr        $3C
.DEFINE count          $3D
.DEFINE tempAddr       $3E   ; 16-bit
.DEFINE rowPtr         $40   ; 16-bit
.DEFINE pointPtr       $42   ; 16-bit
.DEFINE tempByte       $44
.DEFINE tempByte2      $45
.DEFINE plotColor      $46
.DEFINE gridY          $47
.DEFINE freqA          $48
.DEFINE freqB          $49
.DEFINE trailLength    $4A
.DEFINE headAngle      $4B
.DEFINE trailAngle     $4C
.DEFINE freqXPtr       $4D   ; 16-bit
.DEFINE freqYPtr       $4F   ; 16-bit
.DEFINE trailAttrPtr   $51   ; 16-bit
.DEFINE trailTile      $53
.DEFINE trailAttr      $54
.DEFINE speedIndex     $55
.DEFINE colorOffset    $56
.DEFINE curX           $57
.DEFINE curY           $58
.DEFINE prevX          $59
.DEFINE prevY          $5A
.DEFINE validA         $5B
.DEFINE validB         $5C
.DEFINE drawBuffer     $5D
.DEFINE shownBuffer    $5E
.DEFINE shapeIndex     $5F
.DEFINE phase          $60
.DEFINE titleTimer     $61
.DEFINE titleBlink     $62
.DEFINE swapRequest    $63
.DEFINE swapDone       $64
.DEFINE oamDirty       $65
.DEFINE hudLen         $66
.DEFINE hudCount       $67
.DEFINE hudSlot0       $68
.DEFINE hudX0          $69
.DEFINE hudY           $6A
.DEFINE hudAttr        $6B
.DEFINE hudIndex       $6C
.DEFINE tempValue      $6D
.DEFINE brightnessTarget $6E
.DEFINE nameBase       $6F   ; 16-bit
.DEFINE redrawNeeded   $71
.DEFINE hudCount16     $72   ; 16-bit
.DEFINE hudSlot16      $74   ; 16-bit
.DEFINE returnToTitle  $76
.DEFINE neonPhase     $77   ; 0..31, indexes the precomputed floor tables
.DEFINE magiPtr       $78   ; 3 bytes: this frame's VRAM write list
.DEFINE magiCount     $7B
.DEFINE magiPending   $7C
.DEFINE magiTemp      $7D   ; 16-bit scratch used only inside the NMI

; -----------------------------------------------------------------------------
; Work RAM
; -----------------------------------------------------------------------------
.DEFINE pointsA        $0200
.DEFINE pointsB        $0400
.DEFINE oamShadow      $0600  ; 544 bytes
.DEFINE hudBuffer      $0900  ; 16 bytes

; =============================================================================
;  Reset / power-on
; =============================================================================
.BANK 0 SLOT 0
.ORGA $8000

Reset:
  sei
  cld
  clc
  xce
  rep #$30
  ldx #$1FFF
  txs
  lda #$0000
  tcd
  sep #$20
  lda #$00
  pha
  plb

  ; Disable every interrupt/DMA source before touching the PPU.  A flash
  ; cart menu can hand control to the ROM with NMI already enabled.
  stz $4200
  stz $420C
  stz $420D
  lda #$8F
  sta $2100

  ; Clear the low 8 KiB of WRAM (direct page, stack, OAM shadow, HUD buffer).
  ; The 65816 does not clear WRAM on reset, and a flash cart may leave
  ; anything in it.
  rep #$30
  ldx #$0000
  lda #$0000
ResetClearWram:
  sta $0000,x
  inx
  inx
  cpx #$2000
  bne ResetClearWram
  ldx #$1FFF
  txs
  sep #$20

  ; The PPU needs roughly a frame after power-on before its registers and
  ; VRAM/CGRAM ports are usable.  Snes9x accepts early writes, but real
  ; hardware and more accurate emulators may drop them (black screen).
  ; Wait for two complete vblanks before initialising the PPU.
  ldx #$0002
ResetWaitVblank:
  bit $4212
  bpl ResetWaitVblank
ResetWaitVblankEnd:
  bit $4212
  bmi ResetWaitVblankEnd
  dex
  bne ResetWaitVblank
  lda #$8F
  sta $2100

  stz selectedScene
  stz sceneIndex
  stz partyMode
  stz gameParty
  stz themeIndex
  stz hudMode
  stz paused
  stz blackout
  stz transitionState
  stz pendingScene
  stz brightness
  lda #15
  sta masterBrightness
  stz partyTimer
  stz partyTimer+1
  stz hudDirty
  stz frameIndex
  stz frameIndex+1
  stz frameDmaRequest
  stz m7ScrollX
  stz m7ScrollX+1
  stz m7ScrollY
  stz m7ScrollY+1
  stz scrollAccum
  stz scrollAccum+1
  stz titleTimer
  stz titleBlink
  stz prevButtons
  stz prevButtons+1
  stz pressed
  stz pressed+1
  stz frameCounter
  stz frameCounter+1
  stz lastFrame
  stz lastFrame+1
  stz swapRequest
  stz swapDone
  stz oamDirty
  stz returnToTitle
  stz magiPending

  jsr InitTitle
  lda #$81
  sta $4200
  jmp TitleLoop

IrqStub:
  rti

; =============================================================================
;  Main loops
; =============================================================================
TitleLoop:
  jsr WaitFrame
  jsr ReadInput

  ; Up / Down: choose a scene.
  lda pressed+1
  and #$08
  beq TitleNoUp
  lda selectedScene
  bne TitleUpDec
  lda #SCENE_COUNT.B
  dec a
  bra TitleUpStore
TitleUpDec:
  dec a
TitleUpStore:
  sta selectedScene
  jsr TitleChanged
TitleNoUp:
  lda pressed+1
  and #$04
  beq TitleNoDown
  lda selectedScene
  inc a
  cmp #SCENE_COUNT.B
  bcc TitleDownStore
  lda #$00
TitleDownStore:
  sta selectedScene
  jsr TitleChanged
TitleNoDown:

  ; Left / Right / Select: party mode on the menu.
  lda pressed+1
  and #$03
  beq TitleNoLR
  lda partyMode
  eor #$01
  sta partyMode
  jsr TitleChanged
TitleNoLR:
  lda pressed+1
  and #$20
  beq TitleNoSelect
  lda partyMode
  eor #$01
  sta partyMode
  jsr TitleChanged
TitleNoSelect:

  lda pressed+1
  and #$10
  beq TitleNoStart
  jmp StartGame
TitleNoStart:

  jsr AnimateTitle
  jmp TitleLoop

TitleChanged:
  lda selectedScene
  asl a
  ora partyMode
  asl a
  asl a
  sta $2107
  rts

StartGame:
  lda partyMode
  sta gameParty
  stz partyTimer
  stz partyTimer+1
  stz blackout
  lda #15
  sta masterBrightness
  lda gameParty
  beq StartGameFullHud
  lda #1
  bra StartGameHud
StartGameFullHud:
  lda #0
StartGameHud:
  sta hudMode
  lda selectedScene
  sta sceneIndex
  jsr StartScene
  jmp GameLoop

GameLoop:
  jsr WaitFrame
  jsr ReadInput
  jsr HandleGlobalInput
  lda returnToTitle
  beq GameContinue
  stz returnToTitle
  stz $4200
  stz $420C
  jsr InitTitle
  lda #$81
  sta $4200
  jmp TitleLoop
GameContinue:
  jsr UpdateTransition
  jsr UpdateScene
  lda hudDirty
  beq GameNoHud
  jsr UpdateHud
  stz hudDirty
GameNoHud:
  jmp GameLoop

; =============================================================================
;  Input
; =============================================================================
WaitFrame:
  rep #$20
WaitFrameLoop:
  lda frameCounter
  cmp lastFrame
  beq WaitFrameLoop
  sta lastFrame
  sep #$20
WaitJoyReady:
  lda $4212
  and #$01
  bne WaitJoyReady
  rts

ReadInput:
  rep #$30
  lda $4218
  sta buttons
  eor prevButtons
  and buttons
  sta pressed
  lda buttons
  sta prevButtons
  sep #$20
  rts

HandleGlobalInput:
  ; Select returns to the menu.  Do not JMP out of this subroutine: that
  ; would leave its return address on the stack and corrupt it after enough
  ; menu round-trips.  GameLoop sees the flag and performs the switch with a
  ; clean stack.
  lda pressed+1
  and #$20
  beq HandleNoSelect
  lda gameParty
  sta partyMode
  lda #1
  sta returnToTitle
  rts
HandleNoSelect:

  ; Start toggles party mode.
  lda pressed+1
  and #$10
  beq HandleNoStart
  lda gameParty
  eor #$01
  sta gameParty
  stz partyTimer
  stz partyTimer+1
  lda gameParty
  beq HandlePartyOff
  lda #1
  bra HandlePartyHud
HandlePartyOff:
  lda #0
HandlePartyHud:
  sta hudMode
  lda #1
  sta hudDirty
HandleNoStart:

  ; L / R: previous / next scene.
  lda pressed
  and #$20
  beq HandleNoL
  jsr PrevScene
HandleNoL:
  lda pressed
  and #$10
  beq HandleNoR
  jsr NextScene
HandleNoR:

  ; A: blackout toggle.
  lda pressed
  and #$80
  beq HandleNoA
  lda blackout
  eor #$01
  sta blackout
  lda #1
  sta hudDirty
HandleNoA:

  ; B: pause.
  lda pressed+1
  and #$80
  beq HandleNoB
  lda paused
  eor #$01
  sta paused
  lda #1
  sta hudDirty
HandleNoB:

  ; X: colour theme.
  lda pressed
  and #$40
  beq HandleNoX
  lda themeIndex
  inc a
  cmp #4
  bcc HandleStoreTheme
  lda #0
HandleStoreTheme:
  sta themeIndex
  stz $4200
  lda #$8F
  sta $2100
  jsr ApplyTheme
  jsr SetupSceneHdma
  lda brightness
  sta $2100
  lda #$81
  sta $4200
  lda #1
  sta hudDirty
HandleNoX:

  ; Y: toggle the scene-name HUD.
  lda pressed+1
  and #$40
  beq HandleNoY
  lda hudMode
  bne HandleHudShow
  lda #2
  bra HandleStoreHud
HandleHudShow:
  lda #0
HandleStoreHud:
  sta hudMode
  lda #1
  sta hudDirty
HandleNoY:

  ; Up / Down: brightness, or Lissajous frequency B outside party mode.
  lda pressed+1
  and #$08
  beq HandleNoUp
  jsr UpAction
HandleNoUp:
  lda pressed+1
  and #$04
  beq HandleNoDown
  jsr DownAction
HandleNoDown:

  ; Left / Right: Lissajous frequency A outside party mode.
  lda pressed+1
  and #$02
  beq HandleNoLeft
  jsr LeftAction
HandleNoLeft:
  lda pressed+1
  and #$01
  beq HandleNoRight
  jsr RightAction
HandleNoRight:
  rts

UpAction:
  lda gameParty
  bne UpBrightness
  lda sceneIndex
  cmp #4
  beq UpFreqB
UpBrightness:
  lda masterBrightness
  cmp #15
  beq UpDone
  inc a
  sta masterBrightness
  lda #1
  sta hudDirty
UpDone:
  rts
UpFreqB:
  lda freqB
  cmp #FREQ_MAX.B
  beq UpDone
  inc freqB
  lda #1
  sta hudDirty
  rts

DownAction:
  lda gameParty
  bne DownBrightness
  lda sceneIndex
  cmp #4
  beq DownFreqB
DownBrightness:
  lda masterBrightness
  beq DownDone
  dec a
  sta masterBrightness
  lda #1
  sta hudDirty
DownDone:
  rts
DownFreqB:
  lda freqB
  cmp #$02
  bcc DownDone
  dec freqB
  lda #1
  sta hudDirty
  rts

LeftAction:
  lda gameParty
  bne LeftDone
  lda sceneIndex
  cmp #4
  bne LeftDone
  lda freqA
  cmp #$02
  bcc LeftDone
  dec freqA
  lda #1
  sta hudDirty
LeftDone:
  rts

RightAction:
  lda gameParty
  bne RightDone
  lda sceneIndex
  cmp #4
  bne RightDone
  lda freqA
  cmp #FREQ_MAX.B
  beq RightDone
  inc freqA
  lda #1
  sta hudDirty
RightDone:
  rts

PrevScene:
  stz partyTimer
  stz partyTimer+1
  lda sceneIndex
  bne PrevStore
  lda #SCENE_COUNT.B
PrevStore:
  dec a
  sta pendingScene
  lda #1
  sta transitionState
  rts

NextScene:
  stz partyTimer
  stz partyTimer+1
  lda sceneIndex
  inc a
  cmp #SCENE_COUNT.B
  bcc NextStore
  lda #$00
NextStore:
  sta pendingScene
  lda #1
  sta transitionState
  rts

; =============================================================================
;  Scene start / transition
; =============================================================================
StartScene:
  ; Kill NMI/HDMA *before* forced blank: if a vblank NMI landed between the
  ; two writes it would write brightness back to $2100 and un-blank the
  ; screen, and the VRAM uploads below would then run during active display.
  stz $4200
  stz $420C
  lda #$8F
  sta $2100
  stz frameDmaRequest
  stz magiPending
  stz oamDirty
  stz paused
  stz hudDirty
  stz swapRequest
  stz swapDone
  stz frameIndex
  stz frameIndex+1
  stz scrollAccum
  stz scrollAccum+1
  stz m7ScrollX
  stz m7ScrollX+1
  stz m7ScrollY
  stz m7ScrollY+1

  jsr InitOam
  jsr UploadSpriteTiles
  jsr ApplyTheme
  jsr LoadSceneDesc

  lda sceneFlags
  and #$08
  bne StartSceneMagi
  lda sceneFlags
  and #$01
  bne StartSceneLiss
  jsr InitFrameScene
  bra StartSceneDone
StartSceneMagi:
  jsr InitMagiScene
  bra StartSceneDone
StartSceneLiss:
  jsr InitLissajous
StartSceneDone:
  jsr SetupSceneHdma
  jsr UpdateHud
  stz hudDirty
  stz brightness
  lda #2
  sta transitionState
  lda frameCounter
  sta lastFrame
  lda frameCounter+1
  sta lastFrame+1
  lda #$81
  sta $4200
  rts

UpdateTransition:
  lda transitionState
  cmp #1
  beq TransitionOut
  cmp #2
  beq TransitionIn

  ; Idle: ease brightness toward blackout / master level.
  lda blackout
  beq TransitionTargetMaster
  lda #0
  bra TransitionTargetSet
TransitionTargetMaster:
  lda masterBrightness
TransitionTargetSet:
  sta brightnessTarget
  lda brightness
  cmp brightnessTarget
  beq TransitionTargetDone
  bcc TransitionInc
  dec brightness
  bra TransitionTargetDone
TransitionInc:
  inc brightness
TransitionTargetDone:

  ; Party auto-cycle (10 s).
  lda gameParty
  beq TransitionRet
  inc partyTimer
  bne TransitionCheckTimer
  inc partyTimer+1
TransitionCheckTimer:
  lda partyTimer+1
  cmp #$02
  bcc TransitionRet
  bne TransitionCycle
  lda partyTimer
  cmp #$58
  bcc TransitionRet
TransitionCycle:
  stz partyTimer
  stz partyTimer+1
  stz pendingScene
  lda sceneIndex
  inc a
  cmp #SCENE_COUNT.B
  bcc TransitionCycleStore
  lda #$00
TransitionCycleStore:
  sta pendingScene
  lda themeIndex
  inc a
  cmp #4
  bcc TransitionThemeStore
  lda #0
TransitionThemeStore:
  sta themeIndex
  lda #1
  sta transitionState
TransitionRet:
  rts

TransitionOut:
  lda brightness
  beq TransitionSwap
  dec brightness
  rts
TransitionSwap:
  lda pendingScene
  sta sceneIndex
  jsr StartScene
  rts

TransitionIn:
  lda brightness
  cmp masterBrightness
  bcs TransitionInDone
  inc brightness
  rts
TransitionInDone:
  lda #0
  sta transitionState
  rts

; =============================================================================
;  Scene descriptor / init
; =============================================================================
LoadSceneDesc:
  ; Compute the descriptor offset with explicit widths.  An 8-bit X would
  ; leave stale high bits in X, and a 16-bit A would pick up the neighbouring
  ; flag byte; either one makes the indexed reads walk off the table into
  ; zeros.
  rep #$30
  lda sceneIndex
  and #$00FF
  asl a
  asl a
  asl a
  asl a
  tax
  sep #$20

  lda.l SceneDesc+8,x
  sta sceneFlags
  lda.l SceneDesc+6,x
  sta sceneFrameCount
  lda.l SceneDesc+7,x
  sta scrollRate

  lda.l SceneDesc+9,x
  sta sceneScale
  lda.l SceneDesc+10,x
  sta sceneScale+1

  lda.l SceneDesc+12,x
  sta bgSize
  lda.l SceneDesc+13,x
  sta bgSize+1

  lda.l SceneDesc+0,x
  sta bgPtr
  lda.l SceneDesc+1,x
  sta bgPtr+1
  lda.l SceneDesc+2,x
  sta bgPtr+2

  lda.l SceneDesc+3,x
  sta frameTablePtr
  lda.l SceneDesc+4,x
  sta frameTablePtr+1
  lda.l SceneDesc+5,x
  sta frameTablePtr+2

  lda.l SceneDesc+14,x
  sta nameBase
  lda.l SceneDesc+15,x
  sta nameBase+1
  rts

InitFrameScene:
  ; Upload the precomputed Mode 7 image (map entries + pixels).
  lda #$80
  sta $2115
  stz $2116
  stz $2117
  lda bgPtr
  sta dmaSrc
  lda bgPtr+1
  sta dmaSrc+1
  lda bgPtr+2
  sta dmaBank
  lda bgSize
  sta dmaSize
  lda bgSize+1
  sta dmaSize+1
  jsr DmaBankToVram
  jsr SetMode7
  rts

InitLissajous:
  ; The oscilloscope grid is a precomputed Mode 7 background, just like the
  ; other scenes.  Only the comet trail is animated here.
  jsr InitFrameScene
  lda #3
  sta freqA
  lda #2
  sta freqB
  lda #3
  sta speedIndex
  lda #88
  sta trailLength
  stz headAngle
  stz colorOffset
  stz validA
  stz validB
  stz shownBuffer
  lda #1
  sta drawBuffer
  stz swapRequest
  stz swapDone
  stz paused

  jsr SetMode7
  jsr UpdateTrailSprites
  lda #1
  sta oamDirty
  rts

; =============================================================================
;  Pulse Analyzer: Mode 1 monitoring console
;
;  BG1 is the static panel (4bpp, char base 0, map $3400).  BG2 holds the
;  animated cells (4bpp, char base $3000, map $3800) and BG3 the spectrum
;  matrix (2bpp, char base $3000, map $3C00).  BG2 and BG3 share the $3000
;  character base: BG3's single cell tile sits at $3000 and BG2's atlas starts
;  one 16x16 tile later at $3010, which is why the cell map starts at tile 1.
; =============================================================================
InitMagiScene:
  lda #$02
  sta $2101              ; keep the OBJ name base at word $4000
  lda #$80
  sta $2115

  ; BG1 panel tiles -> word $0000.
  lda #<MagiUiTiles.B
  sta dmaSrc
  lda #>MagiUiTiles.B
  sta dmaSrc+1
  lda #:MagiUiTiles.B
  sta dmaBank
  lda #MAGI_UI_TILE_BYTES_LO.B
  sta dmaSize
  lda #MAGI_UI_TILE_BYTES_HI.B
  sta dmaSize+1
  ldx #$0000
  jsr MagiVramUpload

  ; BG3 heat cell + blank tile -> word $3000.
  lda #<MagiHeatTile.B
  sta dmaSrc
  lda #>MagiHeatTile.B
  sta dmaSrc+1
  lda #:MagiHeatTile.B
  sta dmaBank
  lda #$20
  sta dmaSize
  stz dmaSize+1
  ldx #$3000
  jsr MagiVramUpload

  ; BG2 cell atlas -> word $3010 (tile index 1 onward).
  lda #<MagiCellTiles.B
  sta dmaSrc
  lda #>MagiCellTiles.B
  sta dmaSrc+1
  lda #:MagiCellTiles.B
  sta dmaBank
  lda #MAGI_CELL_TILE_BYTES_LO.B
  sta dmaSize
  lda #MAGI_CELL_TILE_BYTES_HI.B
  sta dmaSize+1
  ldx #$3010
  jsr MagiVramUpload

  ; BG1 map -> word $3400.
  lda #<MagiUiMap.B
  sta dmaSrc
  lda #>MagiUiMap.B
  sta dmaSrc+1
  lda #:MagiUiMap.B
  sta dmaBank
  lda #$00
  sta dmaSize
  lda #$08
  sta dmaSize+1
  ldx #MAGI_BG1_MAP
  jsr MagiVramUpload

  ; BG2 map -> word $3800.
  lda #<MagiCellMap.B
  sta dmaSrc
  lda #>MagiCellMap.B
  sta dmaSrc+1
  lda #:MagiCellMap.B
  sta dmaBank
  lda #$00
  sta dmaSize
  lda #$08
  sta dmaSize+1
  ldx #MAGI_BG2_MAP
  jsr MagiVramUpload

  ; BG3 map -> word $3C00 (pre-filled with a full heat waterfall).
  lda #<MagiHeatMap.B
  sta dmaSrc
  lda #>MagiHeatMap.B
  sta dmaSrc+1
  lda #:MagiHeatMap.B
  sta dmaBank
  lda #$00
  sta dmaSize
  lda #$08
  sta dmaSize+1
  ldx #MAGI_BG3_MAP
  jsr MagiVramUpload

  ; Mode 1: BG1/BG2 4bpp, BG3 2bpp, 8x8 tiles.
  lda #$01
  sta $2105
  stz $2106
  lda #$34              ; BG1 map $3400, 32x32
  sta $2107
  lda #$38              ; BG2 map $3800
  sta $2108
  lda #$3C              ; BG3 map $3C00
  sta $2109
  stz $210A
  lda #$30              ; BG1 char $0000, BG2 char $3000
  sta $210B
  lda #$03              ; BG3 char $3000
  sta $210C
  stz $210D
  stz $210D
  stz $210E
  stz $210E
  stz $210F
  stz $210F
  stz $2110
  stz $2110
  stz $2111
  stz $2111
  stz $2112
  stz $2112
  stz $211A
  stz $2133
  stz $2130
  stz $2131

  lda #$17              ; BG1 + BG2 + BG3 + OBJ on the main screen
  sta $212C
  stz $212D

  stz magiPending
  stz frameIndex
  stz frameIndex+1
  rts

; Upload dmaSrc/dmaBank/dmaSize (bytes) to the VRAM word address in X.
MagiVramUpload:
  rep #$20
  txa
  sta $2116
  sep #$20
  jmp DmaBankToVram

; A = 0 for 88x77 Lissajous, or the descriptor scale for precomputed scenes.
SetMode7:
  lda #$07
  sta $2105
  stz $2106
  stz $2107
  stz $2108
  stz $2109
  stz $210A
  stz $210B
  stz $210C
  stz $211A
  stz $2133
  stz $2130
  stz $2131

  lda sceneScale
  sta $211B
  lda sceneScale+1
  sta $211B
  stz $211C
  stz $211C
  stz $211D
  stz $211D
  lda sceneScale
  sta $211E
  lda sceneScale+1
  sta $211E
  stz $211F
  stz $211F
  stz $2120
  stz $2120

  stz $210D
  stz $210D
  stz $210E
  stz $210E

  lda #$11
  sta $212C
  stz $212D
  rts

; =============================================================================
;  Sprite / OAM helpers
; =============================================================================
InitOam:
  sep #$20
  ldx #$0000
  lda #$00
InitOamClear:
  sta oamShadow,x
  inx
  cpx #$0200
  bne InitOamClear
  ldx #$0000
InitOamHide:
  lda #$F0
  sta oamShadow+1,x
  inx
  inx
  inx
  inx
  cpx #$0200
  bne InitOamHide
  ldx #$0200
InitOamHigh:
  stz oamShadow,x
  inx
  cpx #$0220
  bne InitOamHigh
  lda #1
  sta oamDirty
  rts

UploadSpriteTiles:
  ; Font + the three original dot tiles at OBJ word $4000.
  lda #$80
  sta $2115
  stz $2116
  lda #$40
  sta $2117
  lda #<Font4bpp.B
  sta dmaSrc
  lda #>Font4bpp.B
  sta dmaSrc+1
  stz dmaBank
  lda #$60
  sta dmaSize
  lda #$08
  sta dmaSize+1
  jsr DmaBankToVram

  ; Extra scene tiles start at tile 67 (word $4430).
  lda #$80
  sta $2115
  lda #$30
  sta $2116
  lda #$44
  sta $2117
  lda #<ExtraTiles.B
  sta dmaSrc
  lda #>ExtraTiles.B
  sta dmaSrc+1
  lda #:ExtraTiles.B
  sta dmaBank
  lda #EXTRA_TILE_BYTES_LO.B
  sta dmaSize
  lda #EXTRA_TILE_BYTES_HI.B
  sta dmaSize+1
  jsr DmaBankToVram

  lda #$02
  sta $2101
  lda #$80
  sta $2115
  rts

; =============================================================================
;  HUD
; =============================================================================
UpdateHud:
  ; Scene name row.  The demo intentionally keeps the in-game HUD minimal:
  ; the name is white in normal mode and gold in party mode.
  rep #$30
  lda sceneIndex
  and #$00FF
  asl a
  asl a
  asl a
  asl a
  tax
  sep #$20
  lda.l SceneNameTable,x
  cmp #HUD_NAME_LEN.B
  bcc UpdateHudNameLen
  lda #HUD_NAME_LEN.B
UpdateHudNameLen:
  sta hudLen
  ldy #$0000
UpdateHudNameCopy:
  cpy hudLen
  bcs UpdateHudNameCopied
  lda.l SceneNameTable+1,x
  sta hudBuffer,y
  inx
  iny
  bra UpdateHudNameCopy
UpdateHudNameCopied:
  lda hudMode
  cmp #2
  bne UpdateHudNameVisible
  stz hudLen
UpdateHudNameVisible:
  lda #HUD_NAME0.B
  sta hudSlot0
  lda #HUD_NAME_LEN.B
  sta hudCount
  lda #8
  sta hudX0
  lda #8
  sta hudY
  lda #$30
  sta hudAttr
  lda gameParty
  beq UpdateHudNameDraw
  lda #$3E
  sta hudAttr
UpdateHudNameDraw:
  jsr DrawHudRow
  lda #1
  sta oamDirty
  rts

; Draw hudCount slots starting at hudSlot0, using hudBuffer/hudLen.
; X is the slot index; all arithmetic is done with explicit widths so an
; 8-bit variable next to it in the direct page can never leak into X.
DrawHudRow:
  rep #$20
  lda hudCount
  and #$00FF
  sta hudCount16
  lda hudSlot0
  and #$00FF
  sta hudSlot16
  sep #$20
  ldx #$0000
DrawHudLoop:
  cpx hudCount16
  bcs DrawHudDone
  rep #$20
  txa
  clc
  adc hudSlot16
  asl a
  asl a
  clc
  adc #oamShadow
  sta oamPtr
  sep #$20

  txa
  cmp hudLen
  bcs DrawHudHide

  txa
  asl a
  asl a
  asl a
  clc
  adc hudX0
  ldy #$0000
  sta (oamPtr),y
  lda hudY
  sec
  sbc #1
  iny
  sta (oamPtr),y
  lda hudBuffer,x
  iny
  sta (oamPtr),y
  lda hudAttr
  iny
  sta (oamPtr),y
  bra DrawHudNext
DrawHudHide:
  lda #$00
  ldy #$0000
  sta (oamPtr),y
  lda #$F0
  iny
  sta (oamPtr),y
DrawHudNext:
  inx
  jmp DrawHudLoop
DrawHudDone:
  rts

; =============================================================================
;  Lissajous trail (real-time)
; =============================================================================
UpdateTrailSprites:
  rep #$20
  lda freqA
  and #$00FF
  dec a
  asl a
  tax
  lda FreqXPtrs,x
  sta freqXPtr

  lda freqB
  and #$00FF
  dec a
  asl a
  tax
  lda FreqYPtrs,x
  sta freqYPtr

  lda colorOffset
  and #$00FF
  asl a
  tax
  lda TrailAttrPtrs,x
  sta trailAttrPtr

  lda #oamShadow
  sta oamPtr
  sep #$20

  lda headAngle
  sta trailAngle
  stz count

UpdateTrailLoop:
  lda count
  cmp trailLength
  bcc TrailActive
  lda #$00
  sta (oamPtr)
  jsr OamNext
  lda #$F0
  sta (oamPtr)
  jsr OamNext
  lda #$00
  sta (oamPtr)
  jsr OamNext
  lda #$00
  sta (oamPtr)
  jsr OamNext
  bra UpdateTrailNext

TrailActive:
  lda trailAngle
  rep #$20
  and #$00FF
  tay
  sep #$20
  lda (freqXPtr),y
  sta oamX
  lda (freqYPtr),y
  sta oamY

  rep #$20
  lda count
  and #$00FF
  tax
  sep #$20
  lda TrailTiles,x
  sta trailTile

  rep #$20
  lda count
  and #$00FF
  tay
  sep #$20
  lda (trailAttrPtr),y
  sta trailAttr

  lda oamX
  sec
  sbc #$04
  sta (oamPtr)
  jsr OamNext
  lda oamY
  sec
  sbc #$05
  sta (oamPtr)
  jsr OamNext
  lda trailTile
  sta (oamPtr)
  jsr OamNext
  lda trailAttr
  sta (oamPtr)
  jsr OamNext

  lda trailAngle
  sec
  sbc #$01
  sta trailAngle

UpdateTrailNext:
  inc count
  lda count
  cmp #TRAIL_MAX.B
  beq UpdateTrailFinished
  jmp UpdateTrailLoop
UpdateTrailFinished:
  rts

OamNext:
  inc oamPtr
  bne OamNextDone
  inc oamPtr+1
OamNextDone:
  rts

; =============================================================================
;  Scene animation
; =============================================================================
UpdateScene:
  lda paused
  bne UpdateSceneDone
  lda sceneFlags
  and #$01
  bne UpdateSceneLiss

  ; Advance the precomputed OAM frame.
  inc frameIndex
  lda frameIndex
  cmp sceneFrameCount
  bcc UpdateSceneFrameOk
  stz frameIndex
UpdateSceneFrameOk:
  jsr QueueFrame

  ; Pulse Analyzer: request this frame's BG2/BG3 cell writes and BG3 scroll.
  lda sceneFlags
  and #$08
  beq UpdateSceneNoMagi
  lda #1
  sta magiPending
UpdateSceneNoMagi:

  ; Vector City horizontal drift and vertical bob.
  lda sceneFlags
  and #$02
  beq UpdateSceneNoCity
  clc
  lda scrollAccum
  adc scrollRate
  sta scrollAccum
  lda scrollAccum+1
  adc #$00
  sta scrollAccum+1
  lda scrollAccum+1
  sta m7ScrollX
  stz m7ScrollX+1
  ldx frameIndex
  lda.l CityBob,x
  sta m7ScrollY
  stz m7ScrollY+1
UpdateSceneNoCity:

  ; Neon City: advance the per-scanline floor tables one step.
  lda sceneFlags
  and #$04
  beq UpdateSceneDone
  jsr UpdateNeonPhase
  bra UpdateSceneDone

UpdateSceneLiss:
  lda speedIndex
  tax
  lda SpeedValues,x
  clc
  adc headAngle
  sta headAngle
  jsr UpdateTrailSprites
  lda #1
  sta oamDirty
UpdateSceneDone:
  rts

; Advance the Neon City floor by one table step.  Every table holds the whole
; 224-line M7VOFS list, so a step is just a new HDMA source pointer; the band
; of the plane the floor samples is periodic, which makes the wrap at the end
; of the table invisible.
UpdateNeonPhase:
  lda neonPhase
  inc a
  and #$1F
  sta neonPhase
  rep #$30
  and #$00FF
  sta tempAddr
  asl a
  clc
  adc tempAddr
  tax
  sep #$20
  lda.l NeonVTablePtrs,x
  sta $4332
  lda.l NeonVTablePtrs+1,x
  sta $4333
  lda.l NeonVTablePtrs+2,x
  sta $4334
  rts

QueueFrame:
  ; y = frameIndex * 3 (16-bit, because 119*3 = 357)
  rep #$20
  lda frameIndex
  and #$00FF
  sta tempAddr
  asl a
  clc
  adc tempAddr
  tay
  sep #$20
  lda [frameTablePtr],y
  sta frameSrc
  iny
  lda [frameTablePtr],y
  sta frameSrc+1
  iny
  lda [frameTablePtr],y
  sta frameSrc+2
  lda #1
  sta frameDmaRequest
  sta oamDirty
  rts

; =============================================================================
;  Title screen
; =============================================================================
AnimateTitle:
  inc titleTimer
  lda titleTimer
  and #$1F
  bne AnimateTitleDone
  lda titleBlink
  eor #$01
  sta titleBlink
  beq TitleBlinkGold
  lda #$09
  sta $2121
  lda #$DF
  sta $2122
  lda #$5F
  sta $2122
  rts
TitleBlinkGold:
  lda #$09
  sta $2121
  lda #$5F
  sta $2122
  lda #$2F
  sta $2122
AnimateTitleDone:
  rts

InitTitle:
  ; Same ordering as StartScene: no NMI may re-enable the display while the
  ; selector maps and font are being uploaded.
  stz $4200
  stz $420C
  lda #$8F
  sta $2100
  jsr InitOam
  stz oamDirty
  stz swapRequest
  stz swapDone
  stz oamDirty
  stz gameMode
  stz transitionState
  stz redrawNeeded
  lda #0
  sta hudDirty
  lda #15
  sta masterBrightness
  sta brightness

  ; Mode 0, BG1 text layer.  Six scenes * two party states = twelve selector
  ; maps at word 0..$2FFF, font at word $3000.
  stz $2105
  stz $2106
  stz $2107
  stz $2108
  stz $2109
  stz $210A
  lda #$03
  sta $210B
  stz $210C
  stz $2133
  stz $2130
  stz $2131
  stz $2101

  ; Upload the twelve selector maps in one transfer.
  lda #$80
  sta $2115
  stz $2116
  stz $2117
  lda #<SelectorMap0.B
  sta dmaSrc
  lda #>SelectorMap0.B
  sta dmaSrc+1
  lda #:SelectorMap0.B
  sta dmaBank
  lda #$00
  sta dmaSize
  lda #$60              ; six scenes * two party states * 2 KiB
  sta dmaSize+1
  jsr DmaBankToVram

  ; 2bpp font at word $3000.
  lda #$80
  sta $2115
  stz $2116
  lda #$30
  sta $2117
  lda #<Font2bpp.B
  sta dmaSrc
  lda #>Font2bpp.B
  sta dmaSrc+1
  stz dmaBank
  lda #$00
  sta dmaSize
  lda #$04
  sta dmaSize+1
  jsr DmaBankToVram

  ; Title palette.
  stz $2121
  lda #<TitlePalette.B
  sta dmaSrc
  lda #>TitlePalette.B
  sta dmaSrc+1
  lda #(TITLE_COLOR_COUNT*2).B
  sta dmaSize
  stz dmaSize+1
  jsr LoadPaletteCpu

  stz $210D
  stz $210D
  stz $210E
  stz $210E
  lda #$01
  sta $212C
  stz $212D
  lda #$0F
  sta $2100

  lda selectedScene
  asl a
  ora partyMode
  asl a
  asl a
  sta $2107

  lda frameCounter
  sta lastFrame
  lda frameCounter+1
  sta lastFrame+1
  rts

; =============================================================================
;  Palette / theme
; =============================================================================
ApplyTheme:
  stz $420C

  ; Background palette, CGRAM 0..31 (64 colours for the Pulse Analyzer).
  stz $2121
  rep #$30
  lda themeIndex
  and #$00FF
  asl a
  tax
  sep #$20
  lda sceneIndex
  cmp #1
  beq ApplyThemeMagi
  cmp #5
  beq ApplyThemeNeon
  lda.l ThemeBgPtrs,x
  sta dmaSrc
  lda.l ThemeBgPtrs+1,x
  sta dmaSrc+1
  txa                    ; X is theme*2 for the pointers, theme for the banks
  lsr a
  tax
  lda.l ThemeBgBanks,x
  sta dmaBank
  bra ApplyThemeBgUpload
ApplyThemeMagi:
  ; The console owns CGRAM 0..63: eight BG3 heat ramps, then the BG1 and BG2
  ; 4bpp palettes.
  lda.l ThemeBgMagiPtrs,x
  sta dmaSrc
  lda.l ThemeBgMagiPtrs+1,x
  sta dmaSrc+1
  txa
  lsr a
  tax
  lda.l ThemeBgMagiBanks,x
  sta dmaBank
  lda #$80
  sta dmaSize
  stz dmaSize+1
  jsr LoadPaletteBankCpu
  bra ApplyThemeObj
ApplyThemeNeon:
  lda.l ThemeBgNeonPtrs,x
  sta dmaSrc
  lda.l ThemeBgNeonPtrs+1,x
  sta dmaSrc+1
  txa
  lsr a
  tax
  lda.l ThemeBgNeonBanks,x
  sta dmaBank
ApplyThemeBgUpload:
  lda #$40
  sta dmaSize
  stz dmaSize+1
  jsr LoadPaletteBankCpu

  ; Object palettes, CGRAM 128..255.
ApplyThemeObj:
  lda #$80
  sta $2121
  rep #$30
  lda themeIndex
  and #$00FF
  asl a
  tax
  sep #$20
  lda.l ThemeObjPtrs,x
  sta dmaSrc
  lda.l ThemeObjPtrs+1,x
  sta dmaSrc+1
  txa
  lsr a
  tax
  lda.l ThemeObjBanks,x
  sta dmaBank
  lda #$00
  sta dmaSize
  lda #$01
  sta dmaSize+1
  jsr LoadPaletteBankCpu

  ; Per-scene HDMA is configured in StartScene.
  stz $420C
  rts

; Per-scene HDMA.  Channel 0 belongs to the NMI (OAM) and channel 7 to the
; scene DMA helpers, so the effects live on channels 1-4.
SetupSceneHdma:
  stz $420C
  lda sceneIndex
  cmp #2
  beq SetupCityHdma
  cmp #5
  beq SetupNeonHdma
  rts

; Vector City uses HDMA to add a gentle per-scanline M7VOFS wave.  This is a
; real HDMA effect that does not touch CGRAM, so it cannot disturb the palette.
SetupCityHdma:
  lda #$02
  sta $4340
  lda #$0E
  sta $4341
  lda #<CityHdmaTable.B
  sta $4342
  lda #>CityHdmaTable.B
  sta $4343
  lda #:CityHdmaTable.B
  sta $4344
  lda #$10
  sta $420C
  rts

; Neon City rewrites the Mode 7 matrix on every scanline: M7A is the floor
; scale, M7B the shear that keeps the vanishing point on x = 128 and M7VOFS
; the texture row (one of 32 precomputed phases).  Above the horizon the same
; tables keep the skyline at its native 176-texel width.
SetupNeonHdma:
  stz neonPhase

  ; Channel 1: M7A, one 16-bit write per scanline.
  lda #$02
  sta $4310
  lda #$1B
  sta $4311
  lda #<NeonScaleTable.B
  sta $4312
  lda #>NeonScaleTable.B
  sta $4313
  lda #:NeonScaleTable.B
  sta $4314

  ; Channel 2: M7B.
  lda #$02
  sta $4320
  lda #$1C
  sta $4321
  lda #<NeonShearTable.B
  sta $4322
  lda #>NeonShearTable.B
  sta $4323
  lda #:NeonShearTable.B
  sta $4324

  ; Channel 3: M7D (per-scanline depth scale), pointer swaps every step.
  lda #$02
  sta $4330
  lda #$1E
  sta $4331
  lda #<NeonVTable0.B
  sta $4332
  lda #>NeonVTable0.B
  sta $4333
  lda #:NeonVTable0.B
  sta $4334

  lda #$0E
  sta $420C
  rts

; =============================================================================
;  DMA helpers (channel 7 - NMI owns channel 0)
; =============================================================================
DmaZeroToVram:
  stz $4370
  lda #$09
  sta $4370
  lda #$18
  sta $4371
  lda #<ZeroByte.B
  sta $4372
  lda #>ZeroByte.B
  sta $4373
  stz $4374
  lda dmaSize
  sta $4375
  lda dmaSize+1
  sta $4376
  lda #$80
  sta $420B
  rts

; Upload little-endian 16-bit data into $2118/$2119.  VMAIN must be $80.
DmaBankToVram:
  stz $4370
  lda #$01
  sta $4370
  lda #$18
  sta $4371
  lda dmaSrc
  sta $4372
  lda dmaSrc+1
  sta $4373
  lda dmaBank
  sta $4374
  lda dmaSize
  sta $4375
  lda dmaSize+1
  sta $4376
  lda #$80
  sta $420B
  rts

; Upload one byte per VRAM word (Mode 7 map).  VMAIN must be $00.
DmaRomToVramBytes:
  stz $4370
  lda #$18
  sta $4371
  lda dmaSrc
  sta $4372
  lda dmaSrc+1
  sta $4373
  stz $4374
  lda dmaSize
  sta $4375
  lda dmaSize+1
  sta $4376
  lda #$80
  sta $420B
  rts

; Upload a byte stream to CGRAM through $2122.  The caller sets $2121.
LoadPaletteCpu:
  ldy #$0000
  ldx dmaSize
  beq LoadPaletteDone
LoadPaletteLoop:
  lda (dmaSrc),y
  sta $2122
  iny
  dex
  bne LoadPaletteLoop
LoadPaletteDone:
  rts

; Upload a byte stream from any ROM bank to CGRAM through $2122.
; dmaSrc/dmaBank together form the 24-bit source pointer.
LoadPaletteBankCpu:
  ldy #$0000
  ldx dmaSize
  beq LoadPaletteBankDone
LoadPaletteBankLoop:
  lda [dmaSrc],y
  sta $2122
  iny
  dex
  bne LoadPaletteBankLoop
LoadPaletteBankDone:
  rts

; Upload bytes to CGRAM through $2122 with a ROM bank.
DmaBankToCgram:
  stz $4370
  lda #$00
  sta $4370
  lda #$22
  sta $4371
  lda dmaSrc
  sta $4372
  lda dmaSrc+1
  sta $4373
  lda dmaBank
  sta $4374
  lda dmaSize
  sta $4375
  lda dmaSize+1
  sta $4376
  lda #$80
  sta $420B
  rts

; =============================================================================
;  NMI: frame tick, deferred OAM upload, scroll and brightness
; =============================================================================
NmiHandler:
  php
  rep #$30
  pha
  phx
  phy
  sep #$20

  rep #$30
  inc frameCounter
  sep #$20

  lda frameDmaRequest
  beq NmiNoFrame
  ; Scene sprite entries -> WRAM $0600.
  stz $2181
  lda #$06
  sta $2182
  stz $2183
  stz $4370
  lda #$00
  sta $4370
  lda #$80
  sta $4371
  lda frameSrc
  sta $4372
  lda frameSrc+1
  sta $4373
  lda frameSrc+2
  sta $4374
  lda #$80
  sta $4375
  lda #$01
  sta $4376
  lda #$80
  sta $420B

  ; High table -> WRAM $0800.
  stz $2181
  lda #$08
  sta $2182
  stz $2183
  clc
  lda frameSrc
  adc #$80
  sta frameSrc
  lda frameSrc+1
  adc #$01
  sta frameSrc+1
  stz $4370
  lda #$00
  sta $4370
  lda #$80
  sta $4371
  lda frameSrc
  sta $4372
  lda frameSrc+1
  sta $4373
  lda frameSrc+2
  sta $4374
  lda #$18
  sta $4375
  stz $4376
  lda #$80
  sta $420B
  stz frameDmaRequest
NmiNoFrame:

  lda oamDirty
  beq NmiNoOam
  stz $2102
  stz $2103
  stz $4300
  lda #$04
  sta $4301
  lda #<oamShadow.B
  sta $4302
  lda #>oamShadow.B
  sta $4303
  lda #$7E
  sta $4304
  lda #$20
  sta $4305
  lda #$02
  sta $4306
  lda #$01
  sta $420B
  stz oamDirty
NmiNoOam:

  lda magiPending
  beq NmiNoMagi
  lda sceneFlags
  and #$08
  beq NmiNoMagi
  jsr MagiNmiUpdate
  stz magiPending
NmiNoMagi:

  lda m7ScrollX
  sta $210D
  lda m7ScrollX+1
  sta $210D
  lda m7ScrollY
  sta $210E
  lda m7ScrollY+1
  sta $210E

  lda brightness
  sta $2100
  lda #$80
  sta $2115
  rep #$30
  ply
  plx
  pla
  plp
  rti

; =============================================================================
;  Pulse Analyzer: apply one frame of BG2/BG3 cell writes during vblank
;
;  Each frame's list is a byte count followed by (VRAM word address, map
;  entry) pairs.  Only cells that change are listed, so a typical frame is a
;  couple of dozen 16-bit writes; VMAIN is left in the 1-word increment mode.
; =============================================================================
MagiNmiUpdate:
  ; BG3 vertical scroll: the spectrum waterfall moves down two pixels a frame.
  rep #$30
  lda frameIndex
  and #$00FF
  tax
  sep #$20
  lda.l MagiScroll,x
  sta $2112
  stz $2112

  ; 24-bit pointer to this frame's write list (three bytes per frame).
  ; The 65816 only has long,X addressing, so the entry index lives in X.
  rep #$20
  txa
  sta magiTemp
  asl a
  clc
  adc magiTemp
  tax
  sep #$20
  lda.l MagiUpdatePtrs,x
  sta magiPtr
  lda.l MagiUpdatePtrs+1,x
  sta magiPtr+1
  lda.l MagiUpdatePtrs+2,x
  sta magiPtr+2

  lda #$80
  sta $2115
  ldy #$0000
  lda [magiPtr],y
  sta magiCount
  beq MagiNmiDone
  iny
MagiNmiLoop:
  lda [magiPtr],y
  sta $2116
  iny
  lda [magiPtr],y
  sta $2117
  iny
  lda [magiPtr],y
  sta $2118
  iny
  lda [magiPtr],y
  sta $2119
  iny
  dec magiCount
  bne MagiNmiLoop
MagiNmiDone:
  rts

; =============================================================================
;  Mode 7 grid drawing (Lissajous)
; =============================================================================
PlotCurrent:
  lda curX
  asl a
  tax
  lda curY
  asl a
  tay
  jsr PlotPixel
  rts

PlotMidpoint:
  lda prevX
  clc
  adc curX
  lsr a
  asl a
  tax
  lda prevY
  clc
  adc curY
  lsr a
  asl a
  tay
  jsr PlotPixel
  rts

; Plot one pixel.  X = 2*x, Y = 2*y, rowPtr selects the buffer,
; plotColor is the colour index.  VMAIN must be $80.
PlotPixel:
  lda (rowPtr),y
  clc
  adc ColTable,x
  sta tempAddr
  iny
  inx
  lda (rowPtr),y
  adc ColTable,x
  sta tempAddr+1
  lda tempAddr
  sta $2116
  lda tempAddr+1
  sta $2117
  lda plotColor
  sta $2119
  rts

DrawGrid:
  lda #$01
  sta plotColor

  lda #$01
  sta tempByte
  sta gridY
GridTop:
  jsr DrawGridPoint
  inc tempByte
  lda tempByte
  cmp #87
  bne GridTop

  lda #$01
  sta tempByte
  lda #75
  sta gridY
GridBottom:
  jsr DrawGridPoint
  inc tempByte
  lda tempByte
  cmp #87
  bne GridBottom

  lda #$01
  sta tempByte
  sta gridY
GridLeft:
  jsr DrawGridPoint
  inc gridY
  lda gridY
  cmp #76
  bne GridLeft

  lda #86
  sta tempByte
  lda #$01
  sta gridY
GridRight:
  jsr DrawGridPoint
  inc gridY
  lda gridY
  cmp #76
  bne GridRight

  lda #$02
  sta plotColor

  lda #$01
  sta tempByte
  lda #39
  sta gridY
GridHAxis:
  jsr DrawGridPoint
  inc tempByte
  lda tempByte
  cmp #87
  bne GridHAxis

  lda #44
  sta tempByte
  lda #$01
  sta gridY
GridVAxis:
  jsr DrawGridPoint
  inc gridY
  lda gridY
  cmp #76
  bne GridVAxis
  rts

DrawGridPoint:
  lda tempByte
  asl a
  rep #$20
  and #$00FF
  tax
  sep #$20
  lda gridY
  asl a
  rep #$20
  and #$00FF
  tay
  sep #$20
  jsr PlotPixel
  rts

; =============================================================================
;  Static data
; =============================================================================
.INCLUDE "generated.inc"
.INCLUDE "scene_banks.inc"






















