import { Component, OnInit } from '@angular/core';
import { GenericList } from '../util/generic-list';
import { APIService } from '../api.service';
import { ActivatedRoute, Router } from '@angular/router';

@Component({
  selector: 'app-image-search-list',
  templateUrl: './image-search-list.component.html',
  styleUrls: ['./image-search-list.component.css']
})
export class ImageSearchListComponent extends GenericList implements OnInit {

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
