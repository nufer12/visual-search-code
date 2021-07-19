import { Component, OnInit, Input } from '@angular/core';
import { SearchResult, Bbox } from '../util/data-types';
import { APIService } from '../api.service';

@Component({
  selector: 'app-image-results',
  templateUrl: './image-results.component.html',
  styleUrls: ['./image-results.component.scss']
})
export class ImageResultsComponent implements OnInit {

  @Input() imageID : number;
  @Input() collectionID : number;
  @Input() filename : string = null;
  public src : string = '';

  private _zoom : boolean = false;
  @Input()
  get zoom() : boolean {
    return this._zoom;
  }
  set zoom(shouldZoom : boolean) {
    this._zoom = shouldZoom;
    this.calcZoomBBox();
  }

  public aspect : number = 0;

  // Results
  private _results : SearchResult[] = [];
  @Input()
  get results() : SearchResult[] {
    return this._results;
  }
  set results(res : SearchResult[]) {
    this._results = res;
    this._results.forEach(result => {
      result.areas = JSON.parse(result.box_data);
    });
    this.updateView();
  }

  public allResultAreas : {id : number, area: Bbox, search_id: number}[] = [];
  public zoomBbox : Bbox = [0, 0, 100, 100];

  @Input() quality : string = 'thumb';

  changeVote(resID: number, vote: number) {
    this._results.forEach((el, i) => {
      if(el.id == resID) {
        this._results[i].vote = vote;
      }
    })
  }

  constructor(public api : APIService) {
  }

  ngOnInit() {
    this.updateView();
  }

  ngOnDestroy() {
    // super.ngOnDestroy();
    (<any>window).onkeyup = null;
  }

  get wrapper_outer_style() : any {
    // let h_h = this.zoomBbox[1][1] - this.zoomBbox[0][1]; // height in percent of height
    let h_h = this.zoomBbox[3] - this.zoomBbox[1];
    let w_w = this.zoomBbox[2] - this.zoomBbox[0]; // width in percent of width
    let h_w = h_h / this.aspect; // height in percent of width
    let padding = h_w / w_w;
    return {
      'padding-bottom': (padding * 100) + '%'
    }
  }

  get wrapper_inner_style() : any {
    let width = 10000 / (this.zoomBbox[2] - this.zoomBbox[0]);
    let offset_left = 100 * (this.zoomBbox[0] / (this.zoomBbox[2] - this.zoomBbox[0]));
    // top is defined as percentage of height of containing element
    let offset_top = this.zoomBbox[1] / (this.zoomBbox[3] - this.zoomBbox[1]);//  / width; // height in percent of width / width

    return {
      'width': width + '%',
      'left': -offset_left + '%',
      'top': (-offset_top * 100) + '%'
    }
  }


  calcZoomBBox() : void {

    if(!this.zoom) {
      this.zoomBbox = [0, 0, 100, 100];
    } else {
      let all_x = [].concat(...this._results.map(result => {
        return [].concat(...result.areas.map(area => {return [area[0], area[2]]}))
      }));
      let all_y = [].concat(...this._results.map(result => {
        return [].concat(...result.areas.map(area => {return [area[1], area[3]]}))
      }));
      let x = [Math.min(...all_x)*0.9, Math.min(Math.max(...all_x)*1.1, 100)];
      let y = [Math.min(...all_y)*0.9, Math.min(Math.max(...all_y)*1.1, 100)];
      // let x = [Math.min(...all_x), Math.max(...all_x)];
      // let y = [Math.min(...all_y), Math.max(...all_y)];
      this.zoomBbox = [x[0], y[0], x[1], y[1]];
    }

  }

  setSource(quality = 'full') {
    let fname = this.filename;
    if(fname == null) {
      if(this._results.length > 0) {
        fname = this._results[0].filename;
      } else {
        return;
      }
    }

    if(quality == 'thumb') {
      let fnameParts = fname.split('.');
      fname = fnameParts[0] + '.jpg';
    }

    let src = this.api.baseURL+'/img/'+this.collectionID+'/'+quality+'/'+fname+'?token='+this.api.token

    let img = new Image();
    let self = this;
    img.addEventListener('load', function() {
      self.aspect = img.naturalWidth / img.naturalHeight;
      self.src = src;
    });
    img.src = src;

    this.calcZoomBBox();
  }


  ngOnChanges() {
    this.updateView();
  }

  updateView() {
    this.setSource(this.quality);
    this.allResultAreas = [];

    this._results.forEach((res, i) => {
      // flatten areas
      let resAreas = res.areas.map(area => {
        return {id : res.id, area: area, search_id: res.search_id};
      });
      this.allResultAreas = this.allResultAreas.concat(resAreas);
    });
  }

  getBboxStyle(area : Bbox) : {[key : string] : string} {
    return {
      'left': area[0]+'%',
      'top': area[1]+'%',
      'width': (area[2] - area[0]) + '%',
      'height': (area[3] - area[1]) + '%'
    }
  }


}
