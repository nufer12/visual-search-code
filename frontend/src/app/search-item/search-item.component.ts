import { Component, OnInit } from '@angular/core';
import { GenericListItem } from '../util/generic-list';
import { SearchResult, Search, IndexData, IndexStatus } from '../util/data-types';
import { ActivatedRoute } from '@angular/router';
import { APIService } from '../api.service';

@Component({
  selector: 'app-search-item',
  templateUrl: './search-item.component.html',
  styleUrls: ['./search-item.component.scss']
})
export class SearchItemComponent extends GenericListItem<Search> implements OnInit {

  public itemAsSearchResult : SearchResult;
  public collectionID : number;
  public indexName : string;
  public lastRefinementID : number = null;

  public IndexStatus = IndexStatus;

  constructor(private route : ActivatedRoute, private api : APIService) {
    super();
  }

  ngOnInit() {
    this.manageSub('path', this.route.params.subscribe(params => {
      this.collectionID = +params['id'];
    }));
    this.itemAsSearchResult = SearchItemComponent.searchAsResult(<Search>this.item);

    let refinedSearches = JSON.parse(this.item.refined_search) as number[];
    if(refinedSearches && refinedSearches.length > 0) {
      this.lastRefinementID = refinedSearches[refinedSearches.length - 1];
    }

    this.manageSub('index', this.api.getDataByID("indices", this.collectionID, this.item.index_id).subscribe(
      data => {
        if(data) {
          this.indexName = data.typename;
        }
      }
    ))

    
  }

  public static searchAsResult(item: Search) : SearchResult {
    let areas = JSON.parse(item.query_bbox);
    let searchParams = (item.params == "") ? null : JSON.parse(item.params);
    let itemAsSearchResult = {
      id: item.id,
      image_id: item.image_id,
      search_id: item.id,
      score: 0,
      vote: 0,
      box_data: item.query_bbox,
      searchParams: searchParams,
      areas: areas,
      total_boxes: areas.length,
      filename: item.filename,
      refined_searchbox: '[]',
      minscore: 0,
      maxscore: 0
    };
    return itemAsSearchResult;
  }

}
