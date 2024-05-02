# phont

A very basic True-Type Font rendering. Currently, the code is capable of rendering the outline of a glyph and fill the outline (for the most part).

<p align="center">
  <img src="./assets/phont_screenshot.png" width=700 />
</p>

## setup

From within the root directory:
```
pip install -r requirements.txt
python main.py
```

Use the main letter buttons to render different characters.

## todo??

- [x] incorporate bezier curves as well
- [x] allow users to press buttons other than capital letters
- [ ] read the font contents without a special library (`fonttools` in this case)
- [x] fill the font outline
- [ ] show a blinking cursor
- [ ] allow more controls over the font size, color, etc.
- [ ] better and more efficient/smart rendering algorithms:
   - [ ] Signed Distance Field
   - [ ] Improve the existing scanline conversion 
- [ ] maybe some camera effects?

## fonts used for experimenting

I do not own any of the fonts used in this repository. All the fonts are used for experimentation purposes and no commercial use.

- [EB-Garamond](https://github.com/georgd/EB-Garamond)
