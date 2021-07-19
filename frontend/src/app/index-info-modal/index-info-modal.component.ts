import { Component, OnInit, Input, OnChanges } from '@angular/core';
import { ManagedSubs } from '../util/managed-subs';
import { ActivatedRoute } from '@angular/router';
import { APIService } from '../api.service';
import { IndexData } from '../util/data-types';

@Component({
  selector: 'app-index-info-modal',
  templateUrl: './index-info-modal.component.html',
  styleUrls: ['./index-info-modal.component.css']
})
export class IndexInfoModalComponent extends ManagedSubs implements OnInit {

  public collectionID : number;
  public indexList : IndexData[];
  public currentInfoIndex : IndexData;

  constructor(private route : ActivatedRoute, private api : APIService) {
    super();
  }

  private _indexID : number;
  @Input()
  get indexID() : number {
    return this._indexID;
  }
  set indexID(id: number) {
    this._indexID = id;
    if(this.indexList) {
      this.setIndexData();
    }
  }

  setIndexData() {
    if(this.indexList) {
      let _currentIndex = this.indexList.filter(index => {
        return index.id == this._indexID;
      });
      if(_currentIndex.length > 0) {
        this.currentInfoIndex = _currentIndex[0];
      } else {
        this.currentInfoIndex = null;
      }
    }
    
  }

  ngOnInit() {
    this.manageSub('path', this.route.params.subscribe(params => {
      this.collectionID = +params['id'];
      this.manageSub('indices', this.api.data["indices"].get(this.collectionID).subscribe(
        list => {
          if(list) {
            this.indexList = list.data;
            this.setIndexData();
          }
        }
      ));
    }));
  }
}
