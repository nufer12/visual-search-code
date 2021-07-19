import { Component, OnInit } from '@angular/core';
import { ManagedSubs } from '../util/managed-subs';
import {ActivatedRoute} from '@angular/router';
import { APIService } from '../api.service';
import { GenericList } from '../util/generic-list';

@Component({
  selector: 'app-image-list',
  templateUrl: './image-list.component.html',
  styleUrls: ['./image-list.component.css']
})
export class ImageListComponent extends GenericList implements OnInit {

  public collectionID : number = 0;
  public filterScheme = [
    {type: "text", name: "query", placeholder: "Artist, Name, ..."},
    {type: "number", name: "year_from", placeholder: "From", min: -1000, max: 5000, step: 50},
    {type: "number", name: "year_to", placeholder: "To", min: -1000, max: 5000, step: 50},
  ]

  constructor(public api: APIService, private route : ActivatedRoute) {
    super();
  }

  ngOnInit() {
    this.manageSub('path', this.route.params.subscribe(params => {
      this.collectionID = +params['id'];
    }));
  }

}
