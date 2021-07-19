import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { APIService } from '../api.service';
import { ManagedSubs } from '../util/managed-subs';
import { GenericList } from '../util/generic-list';

@Component({
  selector: 'app-search-list',
  templateUrl: './search-list.component.html',
  styleUrls: ['./search-list.component.css']
})
export class SearchListComponent extends GenericList implements OnInit {

  public collectionID : number = 0;
  public filterScheme = [
    {type: "text", name: "query", placeholder: 'Keyword'}
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
