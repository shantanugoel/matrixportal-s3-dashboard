# Font Files for MatrixPortal S3 Dashboard

This directory contains bitmap font files (.bdf format) for the dashboard display.

## Supported Fonts

The system looks for these font files:
- `font5x8.bdf` - Small 5x8 pixel font
- `tom-thumb.bdf` - Tiny 4x6 pixel font  
- `6x10.bdf` - Medium 6x10 pixel font
- `4x6.bdf` - Very tiny 4x6 pixel font

## Getting Font Files

You can download free BDF fonts from:

1. **GNU Unifont**: https://unifoundry.com/unifont/
2. **X11 Fonts**: https://www.x.org/releases/individual/font/
3. **Adafruit Font Packs**: https://github.com/adafruit/Adafruit_CircuitPython_Bitmap_Font

## Popular Small Fonts for LED Matrices

- **tom-thumb**: Very tiny 4x6 font, great for fitting lots of text
- **6x10**: Good balance of readability and size
- **5x8**: Compact but readable
- **4x6**: Maximum text density

## Installation

1. Download `.bdf` font files
2. Copy them to this `fonts/` directory
3. Restart the dashboard
4. The system will automatically detect and use available fonts

## Font Selection

The system automatically chooses the best font size to fit your text:
1. Tries largest font first
2. Falls back to smaller fonts if text doesn't fit
3. Uses bitmap fallback if no BDF fonts available

## Creating Custom Fonts

You can create custom BDF fonts using:
- **FontForge**: Free font editor
- **gbdfed**: BDF-specific editor
- **Online converters**: Convert TTF to BDF

Keep fonts small (under 12 pixels high) for best results on 64x64 displays.
