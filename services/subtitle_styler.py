import pysubs2

class SubtitleStyler:
    def __init__(self, subtitle_source, word_by_word=False):
        """
        Initializes a SubtitleStyler object by loading subtitle data from
        either a file path or Whisper transcription data.
        :param subtitle_source: either a file path to a subtitle file or
        a dictionary/list containing Whisper transcription data
        :precondition subtitle_source: if a file path, must point to a valid
        subtitle file; if Whisper data, must be properly formatted with
        segments structure
        """
        if self.__check_whisper(subtitle_source):
            if word_by_word:
                words = {
                    "segments" : subtitle_source["words"]
                }
                self.__source = pysubs2.load_from_whisper(words)
            else:
                self.__source = pysubs2.load_from_whisper(subtitle_source)
        else:
            self.__source = pysubs2.load(subtitle_source)

        self.__STYLE_FIELD_MAP = {
            "fontFamily": ("fontname", str),
            "fontSize": ("fontsize", self.__parse_px),
            "textColor": ("primarycolor", self.__parse_color),
            "outlineColor": ("outlinecolor", self.__parse_color),
            "backgroundColor": ("backcolor", self.__parse_color),
            "bold": ("bold", self.__ass_bool),
            "italic": ("italic", self.__ass_bool),
            "outlineWidth": ("outline", self.__parse_px),
            "shadow": ("shadow", self.__parse_px),
            "marginl": ("marginl", self.__parse_px),
            "marginr": ("marginr", self.__parse_px),
            "marginv": ("marginv", self.__parse_px),
        }

    def __hex_to_decimal(self, hex, opacity=1):
        """
        Converts a hexadecimal color code to a pysubs2.Color object with
        specified opacity.
        :param hex: a string representing a hexadecimal color code (e.g., "#FFFFFF")
        :param opacity: a float in the range [0,1] representing the opacity level
        :return: a pysubs2.Color object with RGBA values
        """
        hex = hex.lstrip("#")
        r = int(hex[0:2], 16)
        g = int(hex[2:4], 16)
        b = int(hex[4:6], 16)
        color_ratio = 1 - opacity 
        a = round(color_ratio * 255)
        print(a)
        return pysubs2.Color(r, g, b, a)
        
    def __apply_styling(self, style_data):
        """
        Creates a pysubs2.SSAStyle object from the provided style configuration
        dictionary. Applies various text styling properties including font,
        colors, outlines, and positioning.
        :param style_data: a dictionary containing style configuration with
        keys such as "fontFamily", "fontSize", "textColor", "outlineColor",
        "backgroundColor", "bold", "italic", etc.
        :return: a pysubs2.SSAStyle object configured with the specified styling
        """
        kwargs = {"shadow" : 0}
        for client_key, val in style_data.items():
            if client_key not in self.__STYLE_FIELD_MAP:
                continue
            pyKey, parser = self.__STYLE_FIELD_MAP[client_key]
            if client_key == "backgroundColor":
                continue 
            else: 
                kwargs[pyKey] = parser(val)

        return pysubs2.SSAStyle(**kwargs)
    
    def __apply_background_color(self, style_data):
        to_ignore = ("outlineColor", "textColor")
        kwargs = {"borderstyle" : 4}
        for client_key, val in style_data.items():
            if client_key not in self.__STYLE_FIELD_MAP:
                continue
            pyKey, parser = self.__STYLE_FIELD_MAP[client_key]
            if client_key == "backgroundColor":
                kwargs[pyKey] = parser(val, "#000000", style_data.get("backgroundOpacity"))
            elif client_key in to_ignore:
                continue 
            else:
                kwargs[pyKey] = parser(val)
        return pysubs2.SSAStyle(**kwargs)
   

    def implement_styling(self, style_data, path):
        general_style = style_data.get("globalStyle")
        segment_styles = style_data.get("segmentStyles")
        new_events = []
        for id, segment in enumerate(self.__source.events):
            if str(id) in segment_styles:
                print("yerrsss")
                effective_style = {
                    **general_style,
                    **segment_styles[str(id)]
                }
            else:
                effective_style = general_style
            segment_style_event = segment.copy()
            background_style_event = segment.copy()
            style_name = f"style_{id}"
            background_name = f"background_{id}"
            segment_style = self.__apply_styling(effective_style)
            background_style = self.__apply_background_color(effective_style)
            self.__source.styles[style_name] = segment_style
            self.__source.styles[background_name] = background_style
            segment_style_event.style = style_name 
            background_style_event.style = background_name
            background_style_event.layer = 0
            segment_style_event.layer = 1
            new_events.append(background_style_event)
            new_events.append(segment_style_event)
        self.__source.events = new_events
        self.__source.save(path, format_="ass")
            
    def __check_whisper(self, data):
        """
        Validates whether the input data is in Whisper transcription format
        by checking for the presence of required structure elements.

        :param data: input data to validate, can be a dictionary, list, or other type
        :return: a boolean indicating whether the data is valid Whisper format
        :raises ValueError: if the data structure is invalid for either Whisper
        format or standard subtitle processing
        """
        if isinstance(data, dict):
            if "segments" in data and isinstance(data["segments"], list):
                return True 
            else:
                raise ValueError("Invalid source.")
        to_check = all(isinstance(item, dict) for item in data)
        if isinstance(data, list):
            if to_check:
                return True
            else:
                raise ValueError("Invalid source.")
        return False 
    

    def __parse_px(self, px):
        DEFAULT = 12
        if isinstance(px, (int, float)):
            return px
        if isinstance(px, str):
            return float(px.removesuffix('px'))
        return DEFAULT
    
    
    def __parse_color(self, color, default="#FFFFFF", opacity=1):
        if isinstance(color, pysubs2.Color):
            return color
        if not isinstance(color, str) or not color:
            color = default
        color = color.strip()
        if color.startswith("#"):
            raw = color[1:]
        else:
            raw = color
        if len(raw) == 3:
            color = "#" + "".join(char * 2 for char in raw)
        if len(raw) != 6:
            return self.__hex_to_decimal(default)
        
        
        return self.__hex_to_decimal(color, self.__parse_opacity(opacity, 1))

    def __parse_opacity(self, opacity, default=1):
        if opacity is None:
            return default
        try:
            value = float(opacity)
            return max(0, min(1, value))
        except (ValueError, TypeError):
            return default
        
    
    def __ass_bool(self, value):
        return -1 if value else 0
 