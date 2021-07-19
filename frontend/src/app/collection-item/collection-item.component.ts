import { Component, OnInit } from '@angular/core';
import { GenericListItem } from '../util/generic-list';
import { APIService } from '../api.service';
import { Collection } from '../util/data-types';

@Component({
  selector: 'app-collection-item',
  templateUrl: './collection-item.component.html',
  styleUrls: ['./collection-item.component.scss']
})
export class CollectionItemComponent extends GenericListItem<Collection> implements OnInit {

  constructor(public api : APIService) {
    super();
  }

  ngOnInit() {
  }

}
