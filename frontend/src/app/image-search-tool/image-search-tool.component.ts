import { ManagedSubs } from '../util/managed-subs';
import { Component, Input, OnInit, OnDestroy, ViewChild, ElementRef, ChangeDetectorRef} from '@angular/core';
import { APIService } from '../api.service';
import { Bbox} from '../util/data-types';

@Component({
  selector: 'app-image-search-tool',
  templateUrl: './image-search-tool.component.html',
  styleUrls: ['./image-search-tool.component.scss']
})
export class ImageSearchToolComponent extends ManagedSubs implements OnInit {

  @Input() imageID : number;
  @Input() collectionID : number;

  _filename : string = '';
  @Input()
  get filename() : string {
    return this._filename;
  }
  set filename(f : string) {
    this._filename = f;
    this.setSource();
  }
  src : string = '';
  aspect : number = 0;
  padding : string = '';


  @ViewChild('currSearchBoxDiv') currSearchBoxDiv : ElementRef;
  @ViewChild('imageTag') imageTag : ElementRef;
  @ViewChild('outerContainer') outerContainer : ElementRef;


  // search
  searchBoxActive : number = null;
  searchBBoxes : Bbox[] = [];

  editingBox : Bbox = null;


  constructor(public api : APIService, private detector: ChangeDetectorRef) {
    super();
  }

  ngOnInit() {
    this.setSource();
    (<any>window).onkeyup = this.deleteSearchBox.bind(this);
  }

  ngOnDestroy() {
    super.ngOnDestroy();
    (<any>window).onkeyup = null;
  }


  deleteSearchBox(ev) {
    if(this.searchBoxActive != null && (ev.keyCode == 46 || ev.keyCode == 68)) {
      this.searchBBoxes.splice(this.searchBoxActive, 1);
      this.searchBoxActive = null;
    }
  }


  setSource() {
    let src = this.api.baseURL+'/img/'+this.collectionID+'/full/'+this.filename+'?token='+this.api.token;

    let img = new Image();
    let self = this;
    img.addEventListener('load', function() {
      self.aspect = img.naturalWidth / img.naturalHeight;
      self.padding = (100/self.aspect) + '%';
      self.src = src;
    });
    img.src = src;

  }

  toggleSearchBox(ind) {
    if(this.searchBoxActive == ind) {
      this.searchBoxActive = null;
    } else {
      this.searchBoxActive = ind;
    }
  }


  getBboxStyle(area : Bbox) : {[key : string] : string} {
    return {
      'left': area[0]+'%',
      'top': area[1]+'%',
      'width': (area[2] - area[0]) + '%',
      'height': (area[3] - area[1]) + '%'
    }
  }

  getEditBboxStyle() : {[key: string]: string} {
    if(this.editingBox == null) {
      return {}
    }
    let left = Math.min(this.editingBox[0], this.editingBox[2]) + 'px';
    let width = Math.abs(this.editingBox[0] - this.editingBox[2])+'px';
    let top = Math.min(this.editingBox[1], this.editingBox[3]) + 'px';
    let height = Math.abs(this.editingBox[1] - this.editingBox[3])+'px';
    return {
      'left': left,
      'width': width,
      'top': top,
      'height': height
    }
  }

  getEditBboxRelative() {
    let compStyle : any = (<any>window).getComputedStyle(this.imageTag.nativeElement);
    let width : number = +compStyle.getPropertyValue('width').slice(0, -2);
    let height : number = +compStyle.getPropertyValue('height').slice(0, -2);


    this.searchBBoxes.push([
      Math.min(this.editingBox[0], this.editingBox[2])*100/width, Math.min(this.editingBox[1], this.editingBox[3])*100/height,
      Math.max(this.editingBox[0], this.editingBox[2])*100/width, Math.max(this.editingBox[1], this.editingBox[3])*100/height
    ]);

    this.editingBox = null;
  }

  loadBboxIntoEdit(ind : number) {
    let compStyle : any = (<any>window).getComputedStyle(this.imageTag.nativeElement);
    let width : number = +compStyle.getPropertyValue('width').slice(0, -2);
    let height : number = +compStyle.getPropertyValue('height').slice(0, -2);

    this.editingBox = [
      this.searchBBoxes[ind][0]*width/100, this.searchBBoxes[ind][1]*height/100,
      this.searchBBoxes[ind][2]*width/100, this.searchBBoxes[ind][3]*height/100
    ]
  }


  initNewDrawing(ev) {
    this.outerContainer.nativeElement.classList.add('on-creation');
    this.editingBox = [
      ev.layerX, ev.layerY,
      ev.layerX, ev.layerY
    ];
    ev.target.onmousemove = this.followMouse.bind(this);
    ev.preventDefault();
    return false;
  }

  finishNewDrawing(ev) {
    this.outerContainer.nativeElement.classList.remove('on-creation');
    this.editingBox[2] = ev.layerX; this.editingBox[3] = ev.layerY;
    this.imageTag.nativeElement.onmousemove = null;
    this.getEditBboxRelative();
  }


  followMouse(ev) {
    this.editingBox[2] = ev.layerX; this.editingBox[3] = ev.layerY;
    // this.drawEditBbox(ev.layerX, ev.layerY);
  }

}
