import { Component, OnInit, ViewChild, ElementRef } from '@angular/core';
import { ManagedSubs } from '../util/managed-subs';
import { APIService } from '../api.service';
import { ActivatedRoute, Router } from '@angular/router';
import { SearchItemComponent } from '../search-item/search-item.component';
import { SearchResult, Search, IndexData, IndexStatus } from '../util/data-types';
import { GenericList } from '../util/generic-list';
 
@Component({
  selector: 'app-results-list',
  templateUrl: './results-list.component.html',
  styleUrls: ['./results-list.component.scss']
})
export class ResultsListComponent extends GenericList implements OnInit {

  public searchID : number;
  public collectionID: number;
  public queryAsResult : SearchResult;
  public searchData : Search;
  public refinedSearches : Search[];
  public siblingSearches : Search[];
  public relatedSearches : Search[];
  public latestSameIndex : number = 0;
  public baseSearch : Search;
  public indexData : IndexData[];
  public chosenIndexID : number;

  public IndexStatus = IndexStatus;

  private globalZoom : boolean = false;

  // @ViewChild('searchList') searchList : ElementRef;

  constructor(public api: APIService, private route: ActivatedRoute, private router : Router) {
    super();
  }

  ngOnInit() {
    this.manageSub('path', this.route.params.subscribe(params => {
      this.searchID = +params['searchid'];
      // this.searchList.nativeElement.value = this.searchID;
      this.collectionID = +params['id'];
      this.manageSub('searchdata', this.api.getDataByID('searches', this.collectionID, this.searchID).subscribe(
        data => {
          if(data) {
            this.searchData = data;
            this.searchData.searchParams = JSON.parse(this.searchData.params);
            this.queryAsResult = SearchItemComponent.searchAsResult(this.searchData);

            this.manageSub('reloadUntilRetrievals', this.api.data['searchResults'].get(this.searchID).subscribe(retrievals => {
              if(retrievals &&  retrievals.total == 0) {
                setTimeout(_ => {
                  this.api.data['searchResults'].refresh(this.searchID);
                }, 2000);
              }
            }));

            this.baseSearch = null;
            this.manageSub('baseSearchData', this.api.getDataByID('searches', this.collectionID, this.searchData.base_search).subscribe(
              baseSearch => {
                this.baseSearch = baseSearch;
              }
            ))

            this.refinedSearches = [];
            let refinedSearches = JSON.parse(this.searchData.refined_search) as number[];
            if(refinedSearches) {
              refinedSearches.forEach(refinedSearch => {
                this.manageSub('searchData'+refinedSearch, this.api.getDataByID('searches', this.collectionID, refinedSearch).subscribe(
                  refData => {
                    if(refData) {
                      this.refinedSearches.push(refData);
                      this.refinedSearches.sort((a, b) => {
                        return (a.id > b.id) ? 1 : ((b.id > a.id) ? -1 : 0);
                      });
                    }
                  }
                ))
              });
            }

            this.siblingSearches = [];
            this.manageSub('siblingSearches', this.api.data['searchSiblings'].get(this.searchID).subscribe(
              siblings => {
                if(siblings) {
                  this.siblingSearches = siblings.data;
                }
              }
            ));
            this.relatedSearches = [];
            this.manageSub('relatedSearches', this.api.data['searchRelated'].get(this.searchID).subscribe(
              relatedSearches => {
                if(relatedSearches) {
                  this.relatedSearches = relatedSearches.data;
                }
              }
            ));
          }
        }
      ));


      this.manageSub('indexInfo', this.api.data['indices'].get(this.collectionID).subscribe(
        data => {
          if(data != null) {
            this.indexData = data.data;
            this.chosenIndexID = Math.max(...this.indexData.map(el => {
              let ind = (el.status == 4) ? el.id : 0;
              return ind;
            }));
          }
        }
      ));
    }));
  }

  refineSearch() {
    this.api.refineSearch(this.collectionID, this.searchID).then(searchID => {
      setTimeout(_ => {
        this.router.navigate(['collection', this.collectionID, 'search', searchID]);
      }, 0)
    })
  }

  navigateToSearch(ev) {
    if(ev.target.value < 0) {return};
    this.router.navigate(['collection', this.collectionID, 'search', ev.target.value])
  }

  startWithOtherIndex(newIndexID: number) {
    this.api.startSearch(this.collectionID, this.searchData.image_id, newIndexID, JSON.parse(this.searchData.query_bbox), this.searchData.searchParams.combination, this.searchData.searchParams.weights, this.searchData.name, this.searchData.id).then(
      _ => {
        console.log('yep');
      }
    )
  }

  magnifyAll() {
    this.globalZoom = !this.globalZoom;
    window.dispatchEvent(new CustomEvent('focusResults', {detail: this.globalZoom}));
  }

  updateSearchName(ev) {
    this.api.updateSearch(this.collectionID, this.searchID, {name: ev.target.value}).then(data => {
      console.log('updated search name');
    })
  }

}
