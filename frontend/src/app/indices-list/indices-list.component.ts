import { Component, OnInit } from '@angular/core';
import { ManagedSubs } from '../util/managed-subs';
import { IndexData, IndexType, IndexStatus, Collection } from '../util/data-types';
import { APIService } from '../api.service';
import { ActivatedRoute } from '@angular/router';

@Component({
  selector: 'app-indices-list',
  templateUrl: './indices-list.component.html',
  styleUrls: ['./indices-list.component.css']
})
export class IndicesListComponent extends ManagedSubs implements OnInit {

  public indexList : IndexData[];
  public collectionID: number;
  public IndexStatus = IndexStatus;
  public collectionData : Collection;

  constructor(public api : APIService, private route : ActivatedRoute) {
    super();
  }

  ngOnInit() {

    this.manageSub('path', this.route.params.subscribe(params => {
      this.collectionID = +params['id'];
      
      this.manageSub('indices', this.api.data["indices"].get(this.collectionID).subscribe(
        list => {
          if(list) {
            this.indexList = list.data;
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
    }));

    
  }


  rerun(indexID: number) {
    this.api.rerunIndex(this.collectionID, indexID).then(_ => {
      console.log('yolo');
    })
  }

  changeIndexName(newName: string, indexID: number) {
    this.api.updateIndex(this.collectionID, indexID, newName).then(_ => {
      console.log('updated');
    })
  }


}
