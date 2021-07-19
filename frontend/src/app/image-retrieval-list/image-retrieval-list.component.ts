import { Component, OnInit } from '@angular/core';
import { ManagedSubs } from '../util/managed-subs';
import {ActivatedRoute} from '@angular/router';
import { APIService } from '../api.service';
import { GenericList } from '../util/generic-list';

@Component({
  selector: 'app-image-retrieval-list',
  templateUrl: './image-retrieval-list.component.html',
  styleUrls: ['./image-retrieval-list.component.css']
})
export class ImageRetrievalListComponent extends GenericList implements OnInit {
  
    public imageID : number = 0;
    public collectionID : number = 0;
    public paginationSettingsSearches : number[] = [0, 0];
    public bootstrapScale : number;
  
    public filterScheme = [
      {type: "text", name: "query", placeholder: 'Keyword'}
    ]
  
    constructor(public api: APIService, private route : ActivatedRoute) {
      super();
    }
  
    ngOnInit() {
      this.manageSub('path', this.route.params.subscribe(params => {
        this.collectionID = +params['id'];
        this.imageID = +params['imageid'];
     }));
    }
  
  }