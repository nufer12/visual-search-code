import { Component, AfterViewInit, Input, ViewChild, ElementRef, Output, EventEmitter, HostListener } from '@angular/core';
import { SearchResult, Bbox } from '../util/data-types';
import { APIService } from '../api.service';
import { saveAs } from 'file-saver';
import * as b64toBlob from 'b64-to-blob';
// declare const b64toBlob : any;

import 'fabric';
declare const fabric: any;

@Component({
  selector: 'app-image-boxes',
  templateUrl: './image-boxes.component.html',
  styleUrls: ['./image-boxes.component.scss']
})
export class ImageBoxesComponent implements AfterViewInit {

  @ViewChild('imgTag') imgTag : ElementRef; 

  @Input() imageID: number;
  @Input() collectionID : number;
  @Input() filename : string = null;

  @Output() refinedChanged : EventEmitter<any> = new EventEmitter();
  @Output() clicked : EventEmitter<any> = new EventEmitter();

  public refineBoxes : any[] = [];

  private _result : SearchResult = null;
  @Input()
  get result() : SearchResult {
    return this._result;
  }
  set result(res : SearchResult) {
    this._result = res;
    if(res) {
      this.setSource();
    }
  }

  private _isZoomed : boolean = false;

  // TD: nicer
  @Input() quality : string = 'thumb';

  public canvas : any;
  public imageElement : HTMLImageElement = null;
  public src = "";


  public refined : boolean = false;

  constructor(public api : APIService) {
    
  }

  setSource(quality = 'full') {
    let fname = this.result.filename;

    if(quality == 'thumb') {
      let fnameParts = fname.split('.');
      fname = fnameParts[0] + '.jpg';
    }

    let src = this.api.baseURL+'/img/'+this.collectionID+'/'+quality+'/'+fname+'?token='+this.api.token

    this.imageElement = new Image();
    this.imageElement.addEventListener('load', _ => {
      this.drawResult();
      this.src = src;
    });
    this.imageElement.src = src;
  }

  drawResult() {
    this.canvas.clear();
    this.canvas.setViewportTransform([1,0,0,1,0,0]);

    let currentWidth : number = this.imgTag.nativeElement.clientWidth;
    let currentHeight : number = currentWidth * this.imageElement.naturalHeight / this.imageElement.naturalWidth;
    this.canvas.setDimensions({width: currentWidth, height: currentHeight});

    this.canvas.renderAll();

    let imgInstance = new fabric.Image(this.imageElement, {
      left: 0,
      top: 0,
      selectable: false,
      crossOrigin: "anonymous"
    });
    this.canvas.add(imgInstance);
    imgInstance.scaleToWidth(currentWidth);
    imgInstance.scaleToHeight(currentHeight);

    this.refineBoxes = [];
    if(this.result.refined_searchbox && this.result.refined_searchbox.length > 4) {

      this.refined = this.result.refined_searchbox != this.result.box_data;

      let refinedData = JSON.parse(this.result.refined_searchbox) as number[][];
      refinedData.forEach(box => {
        let posData = ImageBoxesComponent.getRectanglePositionObject(box, currentWidth, currentHeight);
        let paramsSelectable = {
          fill: 'transparent',
          strokeWidth: 4,
          stroke: '#AA0A0B',
          lockRotation: true,
          hasRotatingPoint: false,
          left: posData.left - 2,
          top: posData.top - 2,
          width: posData.width,
          height: posData.height,
          cornerColor: 'rgba(0, 0, 0, 0.5)',
          cornerStrokeColor: 'black',
          transparentCorners: false
        }
        this.refineBoxes.push(new fabric.Rect(paramsSelectable));
        this.canvas.add(this.refineBoxes[this.refineBoxes.length - 1]);
        this.refineBoxes[this.refineBoxes.length - 1].on({
          'scaled': _ => {
            this.triggerRefinement();
          },
          'moved': _ => {
            this.triggerRefinement();
          }
        })
      });
    }
    
    this.result.areas = JSON.parse(this.result.box_data) as number[][];
    this.result.areas.forEach(box => {
      let posData = ImageBoxesComponent.getRectanglePositionObject(box, currentWidth, currentHeight);

      if(!this.refined) {
        let paramsOuter = Object.assign({}, posData, {
          fill: 'transparent', 
          selectable: false,
          strokeWidth: 6,
          stroke: 'white',
          left: posData.left - 3,
          top: posData.top - 3
        });
        let rectOuter = new fabric.Rect(paramsOuter);
        this.canvas.add(rectOuter);

        let paramsInner = Object.assign({}, posData, {
          strokeWidth: 2,
          stroke: 'blue',
          fill: 'transparent',
          selectable: false,
          left: posData.left - 1,
          top: posData.top - 1
        });
        let rectInner = new fabric.Rect(paramsInner);
        this.canvas.add(rectInner);
      } else {
        let paramsInner = Object.assign({}, posData, {
          strokeWidth: 2,
          stroke: 'grey',
          fill: 'transparent',
          selectable: false,
          left: posData.left - 1,
          top: posData.top - 1
        });
        let rectInner = new fabric.Rect(paramsInner);
        this.canvas.add(rectInner);
      }
    });
    this._isZoomed = false;
    this.canvas.renderAll();
  }

  static getRectanglePositionObject(data: number[], width: number, height: number) : {left: number, top: number, width: number, height: number} {
    return {
      left: data[0] * width / 100,
      top: data[1] * height / 100,
      width: (data[2] - data[0]) * width / 100,
      height: (data[3] - data[1]) * height / 100
    }
  }

  triggerRefinement() {
    let currentWidth = this.canvas.getWidth();
    let currentHeight = this.canvas.getHeight();
    let newBoxes : number[][] = [];
    this.refineBoxes.forEach(box => {
      let bbox = this.getZoomCompensatedBoundingRect(box);
      newBoxes.push(
        [bbox.left*100/currentWidth, bbox.top*100/currentHeight, (bbox.left + bbox.width)*100/currentWidth, (bbox.top + bbox.height)*100/currentHeight]
      );
    });
    this._result.refined_searchbox = JSON.stringify(newBoxes);
    if(!this.refined) {
      this.drawResult();
    }
    this.refinedChanged.emit(newBoxes);
  }

  getZoomCompensatedBoundingRect(obj){
    //fabricObject is the object you want to get the boundingRect from
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

  saveImage(imageType = 'png') {
    let img = new Image();
    console.log(b64toBlob);
    img.onload = evLoaded => {
        var blob = new Blob([(<any>b64toBlob)(this.canvas.toDataURL(imageType).replace(/^data:image\/(png|jpg);base64,/, ""), "image/" + imageType)], { type: "image/" + imageType });
        saveAs(blob, 'download-searchresult-'+this._result.id+'.' + imageType);
    }
    img.src = this.canvas.toDataURL('image/'+imageType);
  }

  manageSelection(ev) {
    if (ev.selected && ev.selected.length > 1) {
      this.canvas.discardActiveObject();
    }
  }

  @HostListener('window:focusResults', ['$event'])
  focusOnResults(ev? : CustomEvent) {

    let all_x = [].concat(...this.result.areas.map(area => {return [area[0], area[2]]}));
    let all_y = [].concat(...this.result.areas.map(area => {return [area[1], area[3]]}));

    let currentWidth : number = this.imgTag.nativeElement.clientWidth;
    let currentHeight : number = currentWidth * this.imageElement.naturalHeight / this.imageElement.naturalWidth;

    let borderOffset = Math.max(600/currentWidth, 600/currentHeight); // 6px in percent
    

    let x = [0, 100];
    let y = [0, 100];
    if(!this._isZoomed || (ev && ev.detail)) {
      x = [Math.min(...all_x), Math.max(...all_x)];
      y = [Math.min(...all_y), Math.max(...all_y)];
      this._isZoomed = true;
    } else {
      this._isZoomed = false;
    }
    

    let zoom = Math.min(100/(x[1] - x[0] + borderOffset), 100/(y[1] - y[0] + borderOffset));
    let xPx = currentWidth * (x[0] - borderOffset/2)/100;
    let yPx = currentHeight * (y[0] - borderOffset/2)/100;

    this.canvas.setZoom(1);
    this.canvas.viewportTransform[4] = -1*xPx;
    this.canvas.viewportTransform[5] = -1*yPx;
    this.canvas.setZoom(zoom);
    this.canvas.renderAll();
  }



  ngAfterViewInit() {
    this.canvas = new fabric.Canvas('pic-result-canv-'+this.result.id);
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
      if(opt.e.shiftKey === true) {
        this._isZoomed = true;
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

    // this.canvas.on('mouse:down', function(opt) {
      let lastPosX = 0;
      let lastPosY = 0;
      let canLeave = true;
      this.canvas.on('mouse:down', opt => {
        var evt = opt.e;
        if (evt.shiftKey === true) {
          this.canvas.isDragging = true;
          this.canvas.selection = false;
          lastPosX = evt.clientX;
          lastPosY = evt.clientY;
        }
      });
      // this.canvas.on('mouse:move', function(opt) {
      this.canvas.on('mouse:move', opt => {
        if (this.canvas.isDragging) {
          var e = opt.e;
          this.canvas.viewportTransform[4] += e.clientX - lastPosX;
          this.canvas.viewportTransform[5] += e.clientY - lastPosY;
          this.canvas.requestRenderAll();
          lastPosX = e.clientX;
          lastPosY = e.clientY;
        }
      });
      // this.canvas.on('mouse:up', function(opt) {
      this.canvas.on('mouse:up', opt => {
        this.canvas.isDragging = false;
        this.canvas.selection = true;
      });
    this.canvas.on({
      'selection:created': ev => {
        this.manageSelection(ev);
      },
      'selection:updated': ev => {
        this.manageSelection(ev);
      },
      'mouse:dblclick': ev => {
        this.clicked.emit();
      }
    });
  }

  
}
