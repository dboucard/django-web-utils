/**************************************************
* Cover list script                               *
* Author: Stephane Diemer                         *
* License: CC by SA v3                            *
* https://creativecommons.org/licenses/by-sa/3.0/ *
* Requires: jQuery and jQuery ui slider           *
**************************************************/

function CoverList(options) {
    // params
    this.widget_place = "#cover_list";
    this.y_offset = -10;
    this.padding = 3;
    this.box_width = 240 + 2*this.padding;
    this.box_height = 180 + 2*this.padding;
    this.min_size = 0.8;
    this.selected = -1;
    this.color = "#666";
    // vars
    this.$widget = null;
    this.widget_width = 0;
    this.widget_height = 0;
    this.elements = [];
    this.positions = [];
    
    this.allowed_options = [
        "widget_place",
        "padding",
        "box_width",
        "box_height",
        "min_size",
        "selected",
        "color"
    ];
    if (options) {
        this.set_options(options);
        if (options.elements) {
            for (var i=0; i < options.elements.length; i++) {
                this.add_element(options.elements[i]);
            }
        }
    }
    
    var obj = this;
    $(document).ready(function () {
        obj.init_cover_list();
    });
}

CoverList.prototype.set_options = function (options) {
    for (var i = 0; i < this.allowed_options.length; i++) {
        if (this.allowed_options[i] in options)
            this[this.allowed_options[i]] = options[this.allowed_options[i]];
    }
};

/* cover list widget */
CoverList.prototype.add_element = function (ele) {
    var element = {
        index: this.elements.length,
        title: "No title",
        thumb: "",
        url: ""
    };
    for (var field in ele) {
        element[field] = ele[field];
    }
    this.elements.push(element);
};
CoverList.prototype.init_cover_list = function () {
    // Build widget
    var html = "";
    html += "<div class=\"cover-loading\"></div>";
    html += "<div class=\"cover-bar\">";
    html += "    <a class=\"cover-next\" href=\"#\"><span class=\"cover-next-icon\"></span></a>";
    html += "    <div class=\"cover-slider\"></div>";
    html += "    <a class=\"cover-previous\" href=\"#\"><span class=\"cover-previous-icon\"></span></a>";
    html += "</div>";
    this.$widget = $(this.widget_place);
    this.$widget.html(html).addClass("cover-list");
    
    // use only integer and divisible by two values for width and height
    // this is done to avoid having a blurry centered image
    this.widget_width = parseInt(this.$widget.width(), 10);
    if (this.widget_width % 2 != 0)
        this.widget_width --;
    this.widget_height = parseInt(this.$widget.height(), 10);
    if (this.widget_height % 2 != 0)
        this.widget_height --;
    this.calculate_positions();

    if (this.selected < 0)
        this.selected = Math.floor(this.elements.length / 2);
    else if (this.selected >= this.elements.length)
        this.selected = this.elements.length - 1;
    
    this.mode = null;
    try {
        this.canvas_cover_init();
        this.mode = "canvas";
    }
    catch (e) {
        //console.log("Error when trying to initialize cover list in canvas mode: "+e);
    }
    if (this.mode == null) {
        // fallback
        this.html_cover_init();
        this.mode = "html";
    }
    
    // cover bar display
    if (this.elements.length < 2)
        $(".cover-bar", this.widget).css("display", "none");
    else
        $(".cover-bar", this.widget).css("display", "block");
    
    // init events
    var obj = this;
    $(".cover-previous", this.widget).click({ obj: this }, function (e) {
        e.data.obj.go_to_previous();
        return false;
    });
    $(".cover-next", this.widget).click({ obj: this }, function (e) {
        e.data.obj.go_to_next();
        return false;
    });
    $(".cover-slider", this.widget).slider({
        min: 0,
        max: this.elements.length - 1,
        value: this.selected,
        slide: function (event, ui) {
            obj.go_to_index(ui.value);
        },
        stop: function (event, ui) {
            obj.go_to_index(ui.value);
        }
    });
};
CoverList.prototype.calculate_positions = function () {
    if (this.elements.length == 0) {
        this.positions = [];
    }
    else if (this.elements.length == 1) {
        var top = (this.widget_height - this.box_height) / 2 + this.y_offset;
        var offset = (this.widget_width - this.box_width) / 2;
        
        this.positions.push({
            delta: 0,
            factor: 0,
            width: this.box_width,
            height: this.box_height,
            zindex: 1,
            top: top,
            offset: offset
        });
    }
    else {
        var positions_length = this.elements.length;
        var multiplier = 1;
        if (positions_length < 5) {
            multiplier = 0.75;
            if (positions_length < 3)
                multiplier = 0.5;
        }
        for (var i = positions_length; i >= 0; i--) {
            var delta = positions_length - i;
            var factor = delta / positions_length;
            factor = Math.sqrt(factor) * multiplier;
            
            var width = this.box_width * (1 - factor * this.min_size);
            var height = this.box_height * (1 - factor * this.min_size);
            var zindex = positions_length - delta;
            var top = (this.widget_height - height) / 2 + this.y_offset;
            var offset = ((this.widget_width - width) / 2) + (factor * (this.widget_width - width) / 2);
            
            this.positions.push({
                delta: delta,
                factor: factor,
                width: width,
                height: height,
                zindex: zindex,
                top: top,
                offset: offset
            });
        }
    }
};
CoverList.prototype.go_to_index = function (index, update_slider) {
    if (this.mode == "canvas")
        this.canvas_cover_go_to_index(index, update_slider);
    else
        this.html_cover_go_to_index(index, update_slider);
    //console.log("go_to_index", index, this.selected);
};
CoverList.prototype.go_to_previous = function () {
    if (this.mode == "canvas")
        this.canvas_cover_go_to_index(this.selected - 1, true);
    else
        this.html_cover_go_to_index(this.selected - 1, true);
};
CoverList.prototype.go_to_next = function () {
    if (this.mode == "canvas")
        this.canvas_cover_go_to_index(this.selected + 1, true);
    else
        this.html_cover_go_to_index(this.selected + 1, true);
};
CoverList.prototype.hide_loading = function () {
    $(".cover-loading", this.widget).css("display", "none");
};


/* cover list with basic html */
CoverList.prototype.html_cover_init = function () {
    this.hide_loading();
    for (var i = 0; i < this.elements.length; i++) {
        var element = this.elements[i];
        
        var delta = i - this.selected;
        var attrs = this.positions[Math.abs(delta)];
        var position = "top: "+attrs.top+"px; ";
        if (delta < 0)
            position += "left: "+(this.widget_width - attrs.width - attrs.offset)+"px;";
        else
            position += "left: "+attrs.offset+"px;";
        
        var style = "width: "+attrs.width+"px; height: "+attrs.height+"px; z-index: "+attrs.zindex+"; "+position;
        var box = "<div class=\"cover-box\" id=\"cover_box_"+i+"\" style=\""+style+"\">";
        box +=      "<div class=\"cover-box-content\">";
        //box +=          "<div class=\"cover-box-title\">"+element.title+"</div>";
        box +=          "<img src=\""+element.thumb+"\"/>";
        box +=      "</div>";
        box += "</div>";
        box = $(box);
        box.click({ obj: this, index: i }, function (e) {
            e.data.obj.html_cover_select(e.data.index);
        });
        this.$widget.append(box);
    }
};
CoverList.prototype.html_cover_select = function (index) {
    if (index == this.selected) {
        // go to box url
        window.location = this.elements[index].url;
    }
    else {
        // move boxes
        this.html_cover_go_to_index(index, true);
    }
};
CoverList.prototype.html_cover_go_to_index = function (index, update_slider) {
    if (index < 0 || index > this.elements.length - 1 || index == this.selected)
        return;
    this.selected = index;
    for (var i = 0; i < this.elements.length; i++) {
        var delta = i - this.selected;
        var attrs = this.positions[Math.abs(delta)];
        var style = {
            top: attrs.top,
            width: attrs.width,
            height: attrs.height
        };
        if (delta < 0)
            style.left = this.widget_width - attrs.width - attrs.offset;
        else
            style.left = attrs.offset;
        
        var box = $("#cover_box_"+i, this.widget);
        box.stop(true, false);
        box.css("z-index", attrs.zindex);
        box.animate(style, 500);
    }
    if (update_slider)
        $(".cover-slider", this.widget).slider("value", this.selected);
};


/* cover list with html5 canvas */
CoverList.prototype.canvas_cover_init = function () {
    this.$canvas = $("<canvas width=\""+this.widget_width+"\" height=\""+this.widget_height+"\"></canvas>");
    this.$widget.prepend(this.$canvas);
    
    this.canvas = this.$canvas[0];
    this.width = this.canvas.width;
    this.height = this.canvas.height;
    this.ctx = this.canvas.getContext("2d");
    this.animation = {
        duration: 200,
        interval: 25,
        current_time: 0
    };
    
    this.boxes = [];
    this.boxes_dict = {};
    this.nb_images_loaded = 0;
    this.images_loaded = false;
    
    // click events
    $(this.canvas).click({ obj: this }, function (evt) {
        var dom = evt.data.obj.canvas, x_offset = 0, y_offset = 0;
        // get canvas offset
        while (dom != null && dom != undefined) {
            x_offset += dom.offsetLeft;
            y_offset += dom.offsetTop;
            dom = dom.offsetParent;
        }
        var x = evt.pageX - x_offset;
        var y = evt.pageY - y_offset;
        evt.data.obj.canvas_cover_on_click(x, y);
    });
    
    var obj = this;
    var callback = function (success) {
        obj.canvas_cover_on_image_load(success);
    };
    for (var i = 0; i < this.elements.length; i++) {
        var element = this.elements[i];
        
        var delta = i - this.selected;
        var attrs = this.positions[Math.abs(delta)];
        var left;
        if (delta < 0)
            left = this.widget_width - attrs.width - attrs.offset;
        else
            left = attrs.offset;
        
        this.canvas_cover_add_box(new CoverCanvasBox({
            id: i,
            padding: this.padding * (1 - attrs.factor),
            x: left,
            y: attrs.top,
            w: attrs.width,
            h: attrs.height,
            z: attrs.zindex,
            color: this.color,
            thumb: element.thumb,
            url: element.url,
            callback: callback
        }));
    }
};
CoverList.prototype.canvas_cover_on_image_load = function () {
    this.nb_images_loaded++;
    if (this.nb_images_loaded >= this.elements.length) {
        this.images_loaded = true;
        this.hide_loading();
        this.canvas_cover_draw();
    }
};
CoverList.prototype.canvas_cover_go_to_index = function (index, update_slider) {
    if (index < 0 || index > this.elements.length - 1 || index == this.selected)
        return;
    this.selected = index;
    var steps = this.animation.duration / this.animation.interval;
    for (var i = 0; i < this.elements.length; i++) {
        var delta = i - this.selected;
        var attrs = this.positions[Math.abs(delta)];
        var left;
        if (delta < 0)
            left = this.widget_width - attrs.width - attrs.offset;
        else
            left = attrs.offset;
        
        this.boxes_dict["box_"+i].set_target({
            steps: steps,
            padding: this.padding * (1 - attrs.factor),
            x: left,
            y: attrs.top,
            w: attrs.width,
            h: attrs.height,
            z: attrs.zindex,
            color: this.color
        });
    }
    
    this.canvas_cover_animate();
    
    if (update_slider)
        $(".cover-slider", this.widget).slider("value", this.selected);
};
CoverList.prototype.canvas_cover_add_box = function (box) {
    this.boxes.push(box);
    this.boxes_dict["box_"+box.id] = box;
    box.load_image();
};
CoverList.prototype.canvas_cover_draw = function () {
    // get background first
    this.boxes = this.boxes.sort(function (a, b) { return a.z - b.z; });
    // clear canvas
    this.ctx.clearRect(0, 0, this.width, this.height);
    // draw boxes
    for (var i = 0; i < this.boxes.length; i++) {
        this.boxes[i].draw(this.ctx);
    }
};
CoverList.prototype.canvas_cover_on_click = function (x, y) {
    // get foreground first
    var boxes = this.boxes.sort(function (a, b) { return b.z - a.z; });
    // get selected
    for (var i = 0; i < boxes.length; i++) {
        if (boxes[i].contains(x, y)) {
            this.canvas_cover_select(boxes[i]);
            break;
        }
    }
};
CoverList.prototype.canvas_cover_select = function (box) {
    if (box.id == this.selected) {
        // go to box url
        window.location = box.url;
    }
    else {
        // move boxes
        this.canvas_cover_go_to_index(box.id, true);
    }
};
CoverList.prototype.canvas_cover_animate = function () {
    this.animation.current_time = 0;
    this.animation.timeout = null;
    this.canvas_cover_animate_loop();
};
CoverList.prototype.canvas_cover_animate_loop = function () {
    if (this.animation.timeout != null) {
        clearTimeout(this.animation.timeout);
        this.animation.timeout = null;
    }
    if (this.animation.current_time >= this.animation.duration)
        return;
    // draw next step
    for (var i = 0; i < this.boxes.length; i++) {
        this.boxes[i].increment();
    }
    if (this.images_loaded)
        this.canvas_cover_draw();
    // programm next draw
    this.animation.current_time += this.animation.interval;
    var obj = this;
    this.animation.timeout = setTimeout(function () {
        obj.canvas_cover_animate_loop();
    }, this.animation.interval);
};


function CoverCanvasBox(options) {
    this.FIELDS = ["padding", "x", "y", "w", "h", "z"];
    this.id = 0;
    this.padding = 0;
    this.x = 0;
    this.y = 0;
    this.w = 1;
    this.h = 1;
    this.z = 0;
    this.target = {
        padding: 0, padding_step: 0,
        x: 0, x_step: 0,
        y: 0, y_step: 0,
        w: 1, w_step: 0,
        h: 1, h_step: 0,
        z: 0, z_step: 0
    };
    this.color = "#666";
    this.thumb = "";
    this.url = "";
    this.callback = null;
    
    for (var f in options) {
        this[f] = options[f];
    }
    
    this.image = null;
}
CoverCanvasBox.prototype.load_image = function () {
    if (!this.thumb)
        return;
    this.image = new Image();
    this.image.src = this.thumb;
    if (this.callback != null) {
        if (this.image.complete)
            this.callback(this.id, true);
        else {
            var obj = this;
            this.image.onload = function () {
                obj.callback(obj.id, true);
            };
            this.image.onabort = function () {
                obj.callback(obj.id, true);
            };
            this.image.onerror = function () {
                obj.callback(obj.id, false);
            };
        }
    }
};
CoverCanvasBox.prototype.set_target = function (options) {
    var steps = 50;
    if (options.steps)
        steps = options.steps;
    for (var i = 0; i < this.FIELDS.length; i++) {
        var field = this.FIELDS[i];
        if (field in options) {
            this.target[field] = options[field];
            this.target[field+"_step"] = (this.target[field] - this[field]) / steps;
        }
        else {
            this.target[field] = this[field];
            this.target[field+"_step"] = 0;
        }
    }
};
CoverCanvasBox.prototype.increment = function () {
    for (var i = 0; i < this.FIELDS.length; i++) {
        var field = this.FIELDS[i];
        if (this[field] != this.target[field])
            this[field] += this.target[field+"_step"];
    }
};
CoverCanvasBox.prototype.draw = function (ctx) {
    if (!this.image)
        return;
    var x = this.x + this.padding;
    var y = this.y + this.padding;
    var w = this.w - 2*this.padding;
    var h = this.h - 2*this.padding;
    var xr = x;
    var yr = -y - 2*h - 2*this.padding;
    
    ctx.fillStyle = this.color;
    ctx.fillRect(this.x, this.y, this.w, this.h);
    
    ctx.drawImage(this.image, x, y, w, h);
    
    ctx.save(); // save transformation states
    
    // draw reflection
    ctx.scale(1, -1);
    
    ctx.fillStyle = this.color;
    ctx.fillRect(this.x, yr - this.padding, this.w, this.h);
    
    ctx.drawImage(this.image, xr, yr, w, h);
    
    var grad = ctx.createLinearGradient(0, yr, 0, yr + this.h);
    grad.addColorStop(0, "rgba(255, 255, 255, 1)");
    grad.addColorStop(1, "rgba(255, 255, 255, 0.5)");
    ctx.fillStyle = grad;
    ctx.fillRect(this.x, yr - this.padding, this.w, this.h);
    
    ctx.restore(); // retore transformation states
};
CoverCanvasBox.prototype.contains = function (x, y) {
    return x >= this.x && x <= this.x + this.w && y >= this.y && y <= this.y + this.h;
};
