# phont

A very basic True-Type Font rendering.

https://github.com/rhaeguard/phont/assets/23038785/0a89fede-0c71-4ccb-94cf-748a33762784

## setup

From within the root directory:
```
pip install -r requirements.txt
python main.py
```

## todo??

- [x] Incorporate the metrics properly
- [x] Antialiasing (_it's a very simple subpixel antialiasing_)
- [ ] Blinking cursor to show the position.
  - [ ] Allow moving cursor
- [ ] Open a file
- [ ] UI to allow users to select different fonts or open files
  - [ ] Allow more controls over the font size, color, etc.
- [ ] Read the font contents without a special library (`fonttools` in this case)

## fonts used for experimenting

I do not own any of the fonts used in this repository. All the fonts are used for experimentation purposes and no commercial use.

- [EB Garamond](https://github.com/georgd/EB-Garamond)
- [Fira Code](https://github.com/tonsky/FiraCode)
