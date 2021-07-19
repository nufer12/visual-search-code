import { Component, OnInit } from '@angular/core';
import { ManagedSubs } from '../util/managed-subs';
import { Collection } from '../util/data-types';
import { APIService } from '../api.service';
import { ActivatedRoute } from '@angular/router';

@Component({
  selector: 'app-collection-info',
  templateUrl: './collection-info.component.html',
  styleUrls: ['./collection-info.component.css']
})
export class CollectionInfoComponent extends ManagedSubs implements OnInit {

  public collectionID: number;
  public collectionData : Collection;

  constructor(private route: ActivatedRoute, public api : APIService) {
    super();
  }

  ngOnInit() {
    this.manageSub('path', this.route.params.subscribe(params => {
      this.collectionID = +params['id'];

      this.manageSub('collection', this.api.getDataByID<Collection>('collections', 0, this.collectionID).subscribe(
        data => {
          if(data) {
            this.collectionData = data;
          }
        }
      ));
    }));
  }

  updateCollection(title: string, comment: string) {
    this.api.updateCollection(this.collectionID, {name: title, comment: comment}).then(succ => {
    }, error => {
    })
  }

  removeCollection() {
    this.api.removeCollection(this.collectionID).then(succ => {
    }, error => {
    })
  }
  recoverCollection() {
    this.api.recoverCollection(this.collectionID).then(succ => {
    }, error => {
    })
  }

}
