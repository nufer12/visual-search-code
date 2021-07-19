import { Component, OnInit } from '@angular/core';
import { ManagedSubs } from '../util/managed-subs';
import { APIService } from '../api.service';
import { ActivatedRoute, Router } from '@angular/router';
import { Collection } from '../util/data-types';

@Component({
  selector: 'app-collection-page',
  templateUrl: './collection-page.component.html',
  styleUrls: ['./collection-page.component.scss']
})
export class CollectionPageComponent extends ManagedSubs implements OnInit {

  public collectionID : number;
  public collectionData : Collection;
  public activeTab : number | undefined;

  constructor(public api: APIService, private route : ActivatedRoute) {
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
      this.manageSub('activetab', this.route.url.subscribe(() => {
        this.activeTab = this.route.snapshot.firstChild.data.active
      }))
    }));
  }

}
