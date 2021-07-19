import { Component, OnInit, Output, EventEmitter, ViewChild, ElementRef } from '@angular/core';
import { ManagedSubs } from '../util/managed-subs';
import { Search, SearchResult } from '../util/data-types';
import { ActivatedRoute, Router } from '@angular/router';
import { SearchItemComponent } from '../search-item/search-item.component'; 
import { ImageBoxesComponent } from '../image-boxes/image-boxes.component';
import { saveAs } from 'file-saver';
import * as b64toBlob from 'b64-to-blob';

import 'fabric';
import { APIService } from '../api.service';
import { resolve } from 'url';
declare const fabric: any;

@Component({
  selector: 'app-tsne',
  templateUrl: './tsne.component.html',
  styleUrls: ['./tsne.component.scss']
})
export class TsneComponent extends ManagedSubs {

  public collectionID : number;
  public searchID : number;
  public searchData : Search;
  public queryAsResult : SearchResult;
  public searchResults : SearchResult[];

  public canvas : any;

  constructor(private route: ActivatedRoute, private api : APIService, public router : Router) {
    super();
  }

  public _activeResult : SearchResult;
  @Output() activeResult : EventEmitter<SearchResult> = new EventEmitter(null);
  public maxextension : number = 60;
  public showPatches : boolean = false;

  @ViewChild('canvasContainer') canvasContainer : ElementRef;

  ngOnInit() {

    this.manageSub('path', this.route.params.subscribe(params => {
      this.collectionID = +params['id'];
      this.searchID = +params['searchid'];

      this.manageSub('searchData', this.api.getDataByID('searches', this.collectionID, this.searchID).subscribe(
        data => {
          if(data) {
            this.searchData = data;
            this.queryAsResult = SearchItemComponent.searchAsResult(data);

            this.manageSub('searchResults', this.api.data["searchResults"].get(this.searchID).subscribe(results => {
              if(results) {
                this.searchResults = results.data;
                
                this.draw();
              }
              
            }));
          }
        }
      ))

    }));
  }

  draw() {
    if(!this.canvas) {
      this.initCanvas();
    }
    this.canvas.clear();
    this.canvas.setViewportTransform([1,0,0,1,0,0]);
    let currentWidth : number = this.canvasContainer.nativeElement.clientWidth;
    let currentHeight : number = this.canvasContainer.nativeElement.clientWidth * 0.6;
    this.canvas.setDimensions({width: currentWidth, height: currentHeight});

    this.canvas.renderAll();

    this.searchResults.forEach(result => {

      if(!result.tsne || result.tsne == "") {
        return;
      }

      let tsne = JSON.parse(result.tsne);

      let src = this.api.baseURL+'/img/'+this.collectionID+'/thumb/'+result.filename+'?token='+this.api.token;
      fabric.Image.fromURL(src, img => {
        let width = img.width;
        let height = img.height;

        if(this.showPatches) {
          let box = JSON.parse(result.box_data) as number[][];
          let bbox = ImageBoxesComponent.getRectanglePositionObject(box[0], width, height); 
          img.set({cropX: bbox.left, cropY: bbox.top, width: bbox.width, height: bbox.height});
          width = bbox.width;
          height = bbox.height;
        }

        let scale = 1;
        if(width > height) {
          scale = this.maxextension/width;
        } else {
          scale = this.maxextension/height;
        }

        let left = tsne[0] * currentWidth;
        let top = tsne[1] * currentHeight;
        // let left = Math.random() * currentWidth;
        // let top = Math.random() * currentHeight;

        img.set({ left: left, top: top, scaleX: scale, scaleY: scale});
        img.setCoords();
        img.on({
          'mousedown': ev => {
            this.activeResult.emit(result);
            this._activeResult = result;
          },
          
        })

        this.canvas.add(img); 
      }, {
        originX: 'center',
        originY: 'center',
        lockMovementX: true,
        lockMovementY: true,
        lockScalingX: true,
        lockScalingY: true,
        lockUniScaling: true,
        lockRotation: true,
        hasControls: false,
        borderColor: 'red',
        padding: 3
      });
    })
  }

  resetView() {
    this.canvas.setViewportTransform([1,0,0,1,0,0]);
  }

  ngAfterViewInit() {
    if(!this.canvas) {
      this.initCanvas();
    }
    
  }


  initCanvas() {
    this.canvas = new fabric.Canvas('tsne-canvas');
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
        if(this.canvas.isDragging) {
          this.canvas.getObjects().forEach(object => {
            object.setCoords();
          });
        }
        this.canvas.isDragging = false;
        this.canvas.selection = true;
      });
    this.canvas.on({
      'selection:created': ev => {
        this.manageSelection(ev);
      },
      'selection:updated': ev => {
        this.manageSelection(ev);
      }
    });
  }

  manageSelection(ev) {
    if (ev.selected && ev.selected.length > 1) {
      this.canvas.discardActiveObject();
    }
  }

  refineSearch() {
    this.api.refineSearch(this.collectionID, this.searchID).then(searchID => {
      setTimeout(_ => {
        this.router.navigate(['collection', this.collectionID, 'search', searchID]);
      }, 0)
    })
  }

  saveImage(imageType = 'png') {
    let img = new Image();
    console.log(b64toBlob);
    img.onload = evLoaded => {
        var blob = new Blob([(<any>b64toBlob)(this.canvas.toDataURL(imageType).replace(/^data:image\/(png|jpg);base64,/, ""), "image/" + imageType)], { type: "image/" + imageType });
        saveAs(blob, 'download-tsne-'+this.searchID+'.' + imageType);
    }
    img.src = this.canvas.toDataURL('image/'+imageType);
  }

}
