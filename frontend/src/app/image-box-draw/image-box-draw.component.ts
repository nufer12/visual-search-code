import { Component, AfterViewInit, Input, ViewChild, ElementRef, HostListener, Output, EventEmitter } from '@angular/core';
import { APIService } from '../api.service';

import 'fabric';
declare const fabric: any;


@Component({
  selector: 'app-image-box-draw',
  templateUrl: './image-box-draw.component.html',
  styleUrls: ['./image-box-draw.component.scss']
})
export class ImageBoxDrawComponent implements AfterViewInit {

  @ViewChild('imgTag') imgTag : ElementRef; 

  private _src : string;

  @Input()
  get src() : string {
    return this._src;
  }
  set src(s: string) {
    if(s) {
      this._src = s;
      this.imageElement = new Image();
      this.imageElement.addEventListener('load', _ => {
        this.draw();
      });
      this.imageElement.src = this.src;
      console.log(this.src, 'ist src');
    }
  }

  private imageElement : HTMLImageElement = null;
  public canvas : any;

  @Output() boxesUpdated : EventEmitter<number[][]> = new EventEmitter();

  constructor(public api : APIService) {
    
  }

  sendBoxes() {
    let currentWidth = this.canvas.getWidth();
    let currentHeight = this.canvas.getHeight();
    let newBoxes : number[][] = [];
    this.canvas.getObjects().forEach(box => {
      if(box.isSearchRectangle) {
        let bbox = this.getZoomCompensatedBoundingRect(box);
        newBoxes.push(
          [bbox.left*100/currentWidth, bbox.top*100/currentHeight, (bbox.left + bbox.width)*100/currentWidth, (bbox.top + bbox.height)*100/currentHeight]
        );
      }
    });
    this.boxesUpdated.emit(newBoxes);
  }

  draw() {
    this.canvas.clear();
    this.canvas.setViewportTransform([1,0,0,1,0,0]);

    let currentWidth : number = this.imgTag.nativeElement.clientWidth;
    let currentHeight : number = currentWidth * this.imageElement.naturalHeight / this.imageElement.naturalWidth;
    this.canvas.setDimensions({width: currentWidth, height: currentHeight});

    this.canvas.renderAll();

    let imgInstance = new fabric.Image(this.imageElement, {
      left: 0,
      top: 0,
      selectable: false
    });
    
    this.canvas.add(imgInstance);
    imgInstance.scaleToWidth(currentWidth);
    imgInstance.scaleToHeight(currentHeight);

    this.canvas.renderAll();
  }

  getZoomCompensatedBoundingRect(obj){
    obj.setCoords();
    var boundingRect = obj.getBoundingRect();
    let zoom = this.canvas.getZoom();
    var viewportMatrix = this.canvas.viewportTransform;
    boundingRect.top = (boundingRect.top - viewportMatrix[5]) / zoom;
    boundingRect.left = (boundingRect.left - viewportMatrix[4]) / zoom;
    boundingRect.width /= zoom;
    boundingRect.height /= zoom;
    return boundingRect;
  }

  manageSelection(ev) {
    if (ev.selected && ev.selected.length > 1) {
      this.canvas.discardActiveObject();
    }
  }

  private isDrawingMode : boolean = false;
  private isDownDrawing : boolean = false;
  ngAfterViewInit() {
    this.canvas = new fabric.Canvas('draw-canvas');
    this.canvas.on('object:scaling', (e) => {
      var o = e.target;
      if (!o.strokeWidthUnscaled && o.strokeWidth) {
        o.strokeWidthUnscaled = o.strokeWidth;
      }
      if (o.strokeWidthUnscaled) {
        o.strokeWidth = o.strokeWidthUnscaled / o.scaleX;
      }
    });
    this.canvas.on('mouse:wheel', opt => {
      if(opt.e.shiftKey) {
        var delta = opt.e.deltaY;
        var pointer = this.canvas.getPointer(opt.e);
        let speed = (opt.e.shiftKey) ? 80 : 20;
        let zoom = this.canvas.getZoom() + delta/speed;
        if (zoom > 20) zoom = 20;
        if (zoom < 0.01) zoom = 0.01;
        this.canvas.zoomToPoint({ x: opt.e.offsetX, y: opt.e.offsetY }, zoom);
        opt.e.preventDefault();
        opt.e.stopPropagation();
      }
      
    });

    this.canvas.on('mouse:down', function(opt) {
      var evt = opt.e;
      if (evt.shiftKey) {
        this.isDragging = true;
        this.selection = false;
        this.lastPosX = evt.clientX;
        this.lastPosY = evt.clientY;
      }
    });
    this.canvas.on('mouse:move', function(opt) {
      if (this.isDragging) {
        var e = opt.e;
        this.viewportTransform[4] += e.clientX - this.lastPosX;
        this.viewportTransform[5] += e.clientY - this.lastPosY;
        this.requestRenderAll();
        this.lastPosX = e.clientX;
        this.lastPosY = e.clientY;
      }
    });
    this.canvas.on('mouse:up', function(opt) {
      this.isDragging = false;
      this.selection = true;
    });
    this.canvas.on({
      'selection:created': ev => {
        this.manageSelection(ev);
      },
      'selection:updated': ev => {
        this.manageSelection(ev);
      },
    });

    // drawing
    let origX : number, origY: number;
    let rect : any;
    this.canvas.on('mouse:down', opt => {
      this.isDownDrawing = true;
      if(this.isDrawingMode) {
          var pointer = this.canvas.getPointer(opt.e);
          origX = pointer.x;
          origY = pointer.y;
          var pointer = this.canvas.getPointer(opt.e);
          rect = new fabric.Rect({
            left: origX,
            top: origY,
            originX: 'left',
            originY: 'top',
            width: pointer.x - origX,
            height: pointer.y - origY,
            angle: 0,
            fill: 'rgb(255, 0, 0, 0.5)'
          });
          this.canvas.add(rect);
      }
    });
    this.canvas.on('mouse:up', opt => {
      if(this.isDrawingMode) {
        let bbox = this.getZoomCompensatedBoundingRect(rect);
        this.addBoxToCanvas(bbox);
        this.canvas.remove(rect);
      }
      this.isDownDrawing = false;
      this.isDrawingMode = false;
    });
    this.canvas.on('mouse:move', opt => {
      if (!this.isDrawingMode || !this.isDownDrawing) return;
      var pointer = this.canvas.getPointer(opt.e);
      if(origX>pointer.x){
          rect.set({ left: Math.abs(pointer.x) });
      }
      if(origY>pointer.y){
          rect.set({ top: Math.abs(pointer.y) });
      }
      rect.set({ width: Math.abs(origX - pointer.x) });
      rect.set({ height: Math.abs(origY - pointer.y) });
      this.canvas.renderAll();
    });

  }

  addBoxToCanvas(bbox : {width: number, left: number, height: number, top: number}) {
    let drawnRect = new fabric.Rect({
      fill: 'transparent',
      left: bbox.left - 2,
      top: bbox.top - 2,
      width: bbox.width,
      height: bbox.height,
      strokeWidth: 4,
      stroke: '#AA0A0B',
      lockRotation: true,
      hasRotatingPoint: false,
      isSearchRectangle: true,
      cornerColor: 'rgba(0, 0, 0, 0.5)',
      cornerStrokeColor: 'black',
      transparentCorners: false
    });
    drawnRect.on(
      {
        'moved': _ => {
          this.sendBoxes();
        },
        'scaled': _ => {
          this.sendBoxes();
        }
      }
    )
    this.canvas.add(drawnRect);
    this.canvas.renderAll();
    this.sendBoxes();
  }

  removeActiveObjects() {
    let objs = this.canvas.getActiveObjects();
    objs.forEach(obj => {
      this.canvas.remove(obj);
    });
    this.canvas.discardActiveObject();
    this.canvas.renderAll();
    this.sendBoxes();
  }

  @HostListener('window:keydown', ['$event'])
  keyDownEvent(event: KeyboardEvent) {
    if(event.key == 'a') {
      this.isDrawingMode = true;
      this.canvas.hoverCursor = 'crosshair';
      this.canvas.renderAll();
    }
    if(event.key == 'e') {
      this.sendBoxes();
    }
  }
  @HostListener('window:keyup', ['$event'])
  keyUpEvent(event: KeyboardEvent) {
    if(event.key == 'a' && !this.isDownDrawing) {
      this.isDrawingMode = false;
    }
    this.canvas.hoverCursor = null;
  }
  @HostListener('window:keypress', ['$event'])
  keyPressEvent(event: KeyboardEvent) {
    if(event.keyCode == 46) {
      this.removeActiveObjects();
    }
  }

}
