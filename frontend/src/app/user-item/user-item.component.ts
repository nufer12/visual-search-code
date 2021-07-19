import { Component, OnInit } from '@angular/core';
import { GenericListItem } from '../util/generic-list';
import { APIService } from '../api.service';
import { UserData } from '../util/data-types';

@Component({
  selector: 'app-user-item',
  templateUrl: './user-item.component.html',
  styleUrls: ['./user-item.component.css']
})
export class UserItemComponent extends GenericListItem<UserData> implements OnInit {

  constructor(public api : APIService) {
    super();
  }

  ngOnInit() {
  }

}
