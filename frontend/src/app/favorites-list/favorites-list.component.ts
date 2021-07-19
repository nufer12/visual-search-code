import { Component, OnInit } from '@angular/core';
import { ManagedSubs } from '../util/managed-subs';
import { APIService } from '../api.service';
import { ActivatedRoute } from '@angular/router';
import { GenericList } from '../util/generic-list';
import { Search, SearchResult } from '../util/data-types';
import { SearchItemComponent } from '../search-item/search-item.component';

@Component({
  selector: 'app-favorites-list',
  templateUrl: './favorites-list.component.html',
  styleUrls: ['./favorites-list.component.css']
})
export class FavoritesListComponent extends GenericList implements OnInit {

  public collectionID: number;
  public searchID: number;
  public searchData : Search;
  public queryAsResult : SearchResult;

  constructor(public api: APIService, private route: ActivatedRoute) {
    super();
  }

  ngOnInit() {
    this.manageSub('path', this.route.params.subscribe(params => {
      this.collectionID = +params['id'];
      this.searchID = +params['searchid'];

      this.manageSub('searchData', this.api.getDataByID('searches', this.collectionID, this.searchID).subscribe(
        data => {
          if(data) {
            this.searchData = data;
            this.queryAsResult = SearchItemComponent.searchAsResult(data);
          }
        }
      ))

    }));
  }

  magnifyAll() {
    window.dispatchEvent(new Event('focusResults'));
  }

}
