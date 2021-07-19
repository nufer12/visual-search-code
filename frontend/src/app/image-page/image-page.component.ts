import { Component, OnInit, ViewChild, ChangeDetectorRef, OnDestroy } from '@angular/core';
import { APIService } from '../api.service';
import { ActivatedRoute, Router } from '@angular/router';
import { ManagedSubs } from '../util/managed-subs';
import { ImageData, Collection, SearchResult, Worker, IndexData, IndexStatus, Search, IndexType } from '../util/data-types';
import { NotificationService } from '../notification.service';
import { ImageBoxDrawComponent } from '../image-box-draw/image-box-draw.component';
@Component({
  selector: 'app-image-page',
  templateUrl: './image-page.component.html',
  styleUrls: ['./image-page.component.scss']
})
export class ImagePageComponent extends ManagedSubs implements OnInit, OnDestroy {

  public IndexStatus = IndexStatus;

  public collectionID : number;
  public imageID : number;
  public imageData : ImageData = null;
  public indexData : IndexData[] = null;
  public collectionData : Collection = null;
  public latestAvailableIndex : number = 0;

  public mode : number = 0;
  public combine : string = 'AND';
  public searchName : string = '';
  public weight_feature: number = 0.5;
  public weight_angle: number = 0.5;
  public weight_distance: number = 0.5;

  private _chosenIndexID : number = 0;
  public usesLatestImages : boolean = true;
  get chosenIndexID() : number {
    return this._chosenIndexID;
  }
  set chosenIndexID(id: number) {
    this._chosenIndexID = id;
    let indexData = this.indexData.filter(el => {
      return el.id == this._chosenIndexID;
    });
    console.log(indexData);
    if(indexData.length > 0) {
      this.usesLatestImages = indexData[0].is_latest;
    } else {
      this.usesLatestImages = true;
    }
  }


  public workers : Worker[] = [];
  public searchMachine = -1;
  
  
  public paginationSettingsRetrievals : number[] = [0, 0];
  public paginationSettingsSearches : number[] = [0, 0];

  public currentSearchAsResult : Search;
  private currentSearchResultUpdater : any;
  public searchBBoxes : number[][] = [];

  public imageAttributes = ['title', 'artist', 'date', 'genre', 'epoch', 'measurements', 'material', 'technique', 'institution', 'provenance', 'iconclass'];

  @ViewChild('drawCanvas') drawCanvas : ImageBoxDrawComponent;
  
  constructor(private notifier : NotificationService, public api : APIService, private route: ActivatedRoute, private router : Router, private detector: ChangeDetectorRef) {
    super();
  }

  ngOnInit() {
    this.manageSub('path', this.route.params.subscribe(params => {
       this.collectionID = +params['id'];
       this.imageID = +params['imageid'];

       this.updateData();
    }));
  }

  updateData() {
    this.manageSub('imageInfo', this.api.getImageInfo(this.imageID).subscribe(
      data => {
        if(data != null) {
          this.imageData = data;
          this.detector.detectChanges();
        }
      }
    ));
    this.manageSub('indexInfo', this.api.data['indices'].get(this.collectionID).subscribe(
      data => {
        if(data != null) {
          this.indexData = data.data;
          this.latestAvailableIndex = Math.max(...this.indexData.map(el => {
            let ind = (el.status == 5) ? el.id : 0;
            return ind;
          }));
          this.chosenIndexID = this.latestAvailableIndex;
        }

      }
    ));
    this.manageSub('collection', this.api.getDataByID<Collection>('collections', 0, this.collectionID).subscribe(
      data => {
        if(data) {
          this.collectionData = data;
        }
      }
    ));

    this.manageSub("workers", this.api.getWorkers().subscribe(workers => {
      this.workers = workers.filter(worker => {
        return worker.type == 0;
      });
    }));
  }

  deleteImage() {
    this.api.deleteImage(this.imageID, this.collectionID).then(succ => {
      this.updateData();
    }, error => {
      // TODO:
    })
  }

  recoverImage() {
    this.api.recoverImage(this.imageID, this.collectionID).then(succ => {
      this.updateData();
    }, error => {
      // TODO:
    })
  }

  startSearch() {
    // TODO: submit also searchMachine
    this.api.startSearch(this.collectionID, this.imageID, this.chosenIndexID, this.searchBBoxes, this.combine, [this.weight_feature, this.weight_angle, this.weight_distance], this.searchName).then(newSearchID => {
      this.manageSub('currentSearch', this.api.getDataByID('searches', this.collectionID, newSearchID).subscribe(
        data => {
          this.currentSearchAsResult = data;
          document.querySelector('#image-accordion .collapse.show').classList.remove('show');
          document.getElementById('meta-result').classList.add('show');
          if(this.currentSearchAsResult && this.currentSearchAsResult.status <= IndexStatus.RUNNING) {
            this.currentSearchResultUpdater = setTimeout(() => {
              this.api.data['searches'].refresh(this.collectionID);
            }, 5000);
          }
        }
      ))
    }, error => {
      // TODO
    });
  }

  update(ev, field, initValue) {
    if(ev.keyCode == 13) { // enter
      ev.target.disabled = true;
      let data = {};
      data[field] = (ev.target.value.length > 0) ? ev.target.value : null;
      this.api.updateImage(this.imageID, data).then(succ => {
        ev.target.disabled = false;
        ev.target.blur();
      }, error => {
        ev.target.disabled = false;
        ev.target.value = initValue;
      })
    }
    if(ev.keyCode == 27) { // escape
      ev.target.value = initValue;
      ev.target.blur();
    }
  }

  ngOnDestroy() {
    super.ngOnDestroy();
    clearTimeout(this.currentSearchResultUpdater);
  }
}
